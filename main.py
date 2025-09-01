import json
import imaplib
import email
from email.header import decode_header
import requests
import time
import csv
import sys
import re
import os
import unicodedata
import socket
from datetime import datetime

def read_config(file_path):
    with open(file_path, 'r') as file:
        return json.load(file)

def decode_email_subject(subject):
    decoded, encoding = decode_header(subject)[0]
    if isinstance(decoded, bytes):
        decoded = decoded.decode(encoding or 'utf-8', errors='replace')
    return decoded

def get_email_content(email_message):
    content = ""
    if email_message.is_multipart():
        for part in email_message.walk():
            if part.get_content_type() == "text/plain":
                try:
                    part_content = part.get_payload(decode=True).decode(errors='replace')
                except:
                    part_content = part.get_payload()
                content += part_content
    else:
        try:
            content = email_message.get_payload(decode=True).decode(errors='replace')
        except:
            content = email_message.get_payload()
    
    return content.strip()

def is_spam(email_content, api_key, model):
    API_ENDPOINT = "https://api.anthropic.com/v1/messages"

    headers = {
        "Content-Type": "application/json",
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01"
    }

    # Limit email content to 500 characters
    limited_content = email_content[:500]

    data = {
        "model": model,
        "max_tokens": 1000,
        "messages": [
            {"role": "user", "content": f"Is the following email spam? Only respond with 'yes' or 'no'. Here's the first 500 characters of the email: {limited_content}"}
        ]
    }

    try:
        response = requests.post(API_ENDPOINT, headers=headers, json=data)
        response.raise_for_status()
        
        ai_response = response.json()['content'][0]['text'].strip().lower()
        if ai_response not in ['yes', 'yes.','no', 'no.']:
            print(f"Unexpected AI response: {ai_response}")
            return False
        return ai_response == 'yes'
    except requests.exceptions.RequestException as e:
        print(f"Error in API request: {str(e)}")
        if response.status_code == 400:
            print("Error 400: Bad Request. Check your API key and request format.")
        elif response.status_code == 401:
            print("Error 401: Unauthorized. Check your API key.")
        elif response.status_code == 429:
            print("Error 429: Too Many Requests. You may have exceeded your rate limit.")
        else:
            print(f"Unexpected status code: {response.status_code}")
        return False

def is_in_list(email, list_entries):
    email_parts = email.split('@')
    if len(email_parts) != 2:
        return False
    local_part, domain = email_parts

    for entry in list_entries:
        if entry.startswith('*@'):
            if domain.lower() == entry[2:].lower():
                return True
        elif entry.lower() == email.lower():
            return True
    return False

def contains_phishing_patterns(subject, sender, phishing_patterns):
    """Check if email contains known phishing patterns in subject or sender"""
    if not phishing_patterns:
        return False
    
    # Combine subject and sender for pattern matching
    text_to_check = f"{subject} {sender}".lower()
    
    for pattern in phishing_patterns:
        pattern_lower = pattern.lower()
        if pattern_lower in text_to_check:
            return True
    
    return False

def get_tracking_filename(email_address):
    """Generate a unique tracking filename for each email account"""
    safe_email = email_address.replace('@', '_at_').replace('.', '_')
    return f'last_processed_email_{safe_email}.txt'

def load_last_processed_email(email_address):
    """Load the last processed email ID for a specific account"""
    tracking_file = get_tracking_filename(email_address)
    try:
        with open(tracking_file, 'r') as f:
            return f.read().strip()
    except FileNotFoundError:
        print(f"No tracking file found for {email_address}. Starting fresh.")
        return None

def save_last_processed_email_marker(email_address, email_id):
    """Save the last processed email ID for a specific account"""
    tracking_file = get_tracking_filename(email_address)
    try:
        with open(tracking_file, 'w') as f:
            f.write(email_id)
        print(f"Saved last processed email ID for {email_address}: {email_id}")
    except Exception as e:
        print(f"Error saving tracking file for {email_address}: {str(e)}")

def strip_control_characters(s):
    return "".join(ch for ch in s if unicodedata.category(ch)[0] != "C")

def sanitize_string(s):
    # Replace problematic characters with their names or a placeholder
    return ''.join(c if ord(c) < 65536 else f'[U+{ord(c):X}]' for c in s)

def check_imap_server(server, port, timeout=5):
    try:
        socket.setdefaulttimeout(timeout)
        socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect((server, port))
        return True
    except socket.error as e:
        return False

def process_emails(config, api_key):
    imap_server = config['imap_server']
    imap_port = config['imap_port']
    email_address = config['email_address']
    
    # Check IMAP server availability
    if not check_imap_server(imap_server, imap_port):
        print(f"Error: Unable to connect to the IMAP server ({imap_server}:{imap_port}).")
        print("Please check your internet connection and verify the IMAP server details.")
        print("If the problem persists, contact your email provider or system administrator.")
        return 0, 0

    mail = imaplib.IMAP4_SSL(imap_server, imap_port)
    spam_count = 0
    whitelist = config.get('whitelist', [])
    blacklist = config.get('blacklist', [])
    phishing_patterns = config.get('phishing_patterns', [])
    only_gather_metrics = config.get('OnlyGatherMetrics', False)
    skip_ai = config.get('SkipAI', False)
    csv_file = "./output/" + config.get('MetricsCSVFile', 'metrics.csv')
    model = config.get('AIModel', 'claude-3-opus-20240229')
    max_emails_before_stopping = config.get('MaxEmailsBeforeStopping', 50)
    
    metrics = []
    processed_email_count = 0
    first_non_spam_email_id = None  # Track the first (newest) NON-SPAM email processed
    found_last_processed = False  # Flag to break out of nested loops
    
    try:
        mail.login(email_address, config['password'])
        mail.select('INBOX')
        
        _, message_numbers = mail.search(None, 'ALL')
        message_numbers = message_numbers[0].split()
        message_numbers.reverse()  # Process from newest to oldest
        
        # Load the last processed email for THIS specific account
        last_processed_email = load_last_processed_email(email_address)
        print(f"Last processed email for {email_address}: {last_processed_email}")
        
        for num in message_numbers:
            if processed_email_count >= max_emails_before_stopping:
                print(f"Reached maximum email count of {max_emails_before_stopping}. Stopping processing.")
                break
            
            if found_last_processed:  # Break out of outer loop if we found the last processed email
                break
            
            try:
                _, msg = mail.fetch(num, '(BODY.PEEK[])')
                
                for response in msg:
                    if isinstance(response, tuple):
                        email_message = email.message_from_bytes(response[1])
                        message_id = email_message['Message-ID']
                        
                        # If we found the last processed email, stop here
                        if message_id != None and message_id == last_processed_email:
                            print(f"Found last processed email for {email_address}. Stopping.")
                            found_last_processed = True  # Set flag to break out of outer loop
                            break  # Break out of inner loop
                        
                        subject = decode_email_subject(email_message["Subject"])
                        print(f"Subject: {subject}")
                        subject = sanitize_string(strip_control_characters(subject))
                        sender = sanitize_string(strip_control_characters(email_message["From"]))
                        sender_email = re.search(r'<(.+?)>', sender)
                        if sender_email:
                            sender_email = sender_email.group(1)
                        else:
                            sender_email = sender
                        
                        status = ""
                        is_spam_email = False  # Track if this email is spam
                        
                        # Check whitelist
                        if is_in_list(sender_email, whitelist):
                            print(f"WHITE:\t{sender}:\t{subject}\t{message_id}")
                            status = "WHITE"
                            
                        # Check blacklist
                        elif is_in_list(sender_email, blacklist):
                            print(f"BLACK:\t{sender}:\t{subject}\t{message_id}")
                            status = "BLACK"
                            is_spam_email = True  # This is spam
                            if not only_gather_metrics:
                                try:
                                    mail.copy(num, 'Junk')
                                    mail.store(num, '+FLAGS', '\\Deleted')
                                except Exception as e:
                                    print(f"Error moving email to Junk: {str(e)}")
                            spam_count += 1
                        
                        # Check phishing patterns
                        elif contains_phishing_patterns(subject, sender, phishing_patterns):
                            print(f"PHISH:\t{sender}:\t{subject}\t{message_id}")
                            status = "PHISH"
                            is_spam_email = True  # This is spam
                            if not only_gather_metrics:
                                try:
                                    mail.copy(num, 'Junk')
                                    mail.store(num, '+FLAGS', '\\Deleted')
                                except Exception as e:
                                    print(f"Error moving email to Junk: {str(e)}")
                            spam_count += 1
                        
                        else:
                            content = get_email_content(email_message)
                            
                            if content:
                                if skip_ai:
                                    # When SkipAI is true, just log the email without AI processing
                                    print(f"SKIPPED:\t{sender}:\t{subject}\t{message_id}")
                                    status = "SKIPPED"
                                else:
                                    if is_spam(content, api_key, model):
                                        print(f"SPAM:\t{sender}:\t{subject}\t{message_id}")
                                        status = "SPAM"
                                        is_spam_email = True  # This is spam
                                        if not only_gather_metrics:
                                            try:
                                                mail.copy(num, 'Junk')
                                                mail.store(num, '+FLAGS', '\\Deleted')
                                            except Exception as e:
                                                print(f"Error moving email to Junk: {str(e)}")
                                        spam_count += 1
                                    else:
                                        print(f"FINE:\t{sender}:\t{subject}\t{message_id}")
                                        status = "FINE"
                            else:
                                print(f"EMPTY:\t{sender}:\t{subject}\t{message_id}")
                                status = "EMPTY"
                        
                        if only_gather_metrics:
                            metrics.append([status, sender, subject])
                        
                        processed_email_count += 1
                        
                        # FIXED BUG: Save the first NON-SPAM email processed
                        # Spam emails (BLACK and SPAM) get deleted, so we can't find them next time
                        # Save the first non-spam email instead
                        if first_non_spam_email_id is None and not is_spam_email:
                            first_non_spam_email_id = message_id
                            print(f"DEBUG: Saving first non-spam email: {message_id}")
                                            
                        #time.sleep(1/10) #throttle in seconds. 1/10 says process a max of 10 emails/second
            except Exception as e:
                print(f"Error processing email: {str(e)}")
                continue  # Skip this email and move to the next one
            
            if processed_email_count >= max_emails_before_stopping:
                print(f"DONE:\t{max_emails_before_stopping} emails processed.")
                break
        
        if not only_gather_metrics:
            mail.expunge()
        
        # Check if we found the last processed email (no new emails to process)
        #if found_last_processed and processed_email_count == 0:
        #    print(f"No new emails to process for {email_address}")
        # FIXED: Save the first NON-SPAM email processed
        # This ensures next run stops when it encounters this email (which won't be deleted)
        if first_non_spam_email_id and processed_email_count > 0:
            save_last_processed_email_marker(email_address, first_non_spam_email_id)
            print(f"Successfully processed {processed_email_count} new emails for {email_address}")
        elif processed_email_count > 0:
            print(f"WARNING: All {processed_email_count} emails were spam - no tracking marker saved!")
            print("Next run will reprocess these emails.")
        else:
            print(f"No new emails to process for {email_address}")

    except imaplib.IMAP4.error as e:
        print(f"IMAP error occurred: {str(e)}")
        print("This could be due to incorrect login credentials or server issues.")
        print("Please check your email address and password in the config file.")
    except Exception as e:
        print(f"An error occurred: {str(e)}")
    finally:
        try:
            mail.close()
            mail.logout()
        except:
            pass  # Ignore errors during logout if connection was never established
    
    if only_gather_metrics and metrics:
        with open(csv_file, 'w', newline='', encoding='utf-8') as file:
            writer = csv.writer(file)
            writer.writerow(['Status', 'Sender', 'Subject'])
            writer.writerows(metrics)
        print(f"Metrics saved to {csv_file}")
    
    return spam_count, processed_email_count

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python main.py <config_file_path>")
        sys.exit(1)

    config_file_path = sys.argv[1]
    try:
        config = read_config(config_file_path)
    except FileNotFoundError:
        print(f"Error: Config file '{config_file_path}' not found.")
        sys.exit(1)
    except json.JSONDecodeError:
        print(f"Error: Invalid JSON in config file '{config_file_path}'.")
        sys.exit(1)

    api_key = config.get('ANTHROPIC_API_KEY')
    if not api_key:
        print("Error: ANTHROPIC_API_KEY not found in config file.")
        sys.exit(1)

    total_spam, total_processed = process_emails(config, api_key)
    print(f"Total emails processed: {total_processed}")
    print(f"Total {'potential' if config.get('OnlyGatherMetrics', False) else ''} emails {'that would be' if config.get('OnlyGatherMetrics', False) else ''} moved to Junk folder: {total_spam}")
