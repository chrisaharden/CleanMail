import json
import imaplib
import email
from email.header import decode_header
import requests
import time
import csv
import sys
import re

def read_config(file_path):
    with open(file_path, 'r') as file:
        return json.load(file)

def decode_email_subject(subject):
    decoded, encoding = decode_header(subject)[0]
    if isinstance(decoded, bytes):
        decoded = decoded.decode(encoding or 'utf-8')
    return decoded

def get_email_content(email_message):
    content = ""
    if email_message.is_multipart():
        for part in email_message.walk():
            if part.get_content_type() == "text/plain":
                try:
                    part_content = part.get_payload(decode=True).decode()
                except:
                    part_content = part.get_payload()
                content += part_content
    else:
        try:
            content = email_message.get_payload(decode=True).decode()
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

def process_emails(config, api_key):
    mail = imaplib.IMAP4_SSL(config['imap_server'], config['imap_port'])
    spam_count = 0
    whitelist = config.get('whitelist', [])
    blacklist = config.get('blacklist', [])
    only_gather_metrics = config.get('OnlyGatherMetrics', False)
    csv_file = "./output/" + config.get('MetricsCSVFile', 'metrics.csv')
    max_email_count = config.get('MetricsMaxEmailCount', float('inf'))
    model = config.get('AIModel', 'claude-3-opus-20240229')
    
    metrics = []
    processed_email_count = 0
    
    try:
        mail.login(config['email_address'], config['password'])
        mail.select('INBOX')
        
        _, message_numbers = mail.search(None, 'ALL')
        
        for num in message_numbers[0].split():
            if processed_email_count >= max_email_count:
                print(f"Reached maximum email count of {max_email_count}. Stopping processing.")
                break
            
            _, msg = mail.fetch(num, '(RFC822)')
            
            for response in msg:
                if isinstance(response, tuple):
                    email_message = email.message_from_bytes(response[1])
                    subject = decode_email_subject(email_message["Subject"])
                    sender = email_message["From"]
                    sender_email = re.search(r'<(.+?)>', sender)
                    if sender_email:
                        sender_email = sender_email.group(1)
                    else:
                        sender_email = sender
                    
                    status = ""
                    
                    # Check whitelist
                    if is_in_list(sender_email, whitelist):
                        print(f"WHITE:\t{sender}:\t{subject}")
                        status = "WHITE"
                        
                    # Check blacklist
                    elif is_in_list(sender_email, blacklist):
                        print(f"BLACK:\t{sender}:\t{subject}")
                        status = "BLACK"
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
                            if is_spam(content, api_key, model):
                                print(f"SPAM:\t{sender}:\t{subject}")
                                status = "SPAM"
                                if not only_gather_metrics:
                                    try:
                                        mail.copy(num, 'Junk')
                                        mail.store(num, '+FLAGS', '\\Deleted')
                                    except Exception as e:
                                        print(f"Error moving email to Junk: {str(e)}")
                                spam_count += 1
                            else:
                                print(f"FINE:\t{sender}:\t{subject}")
                                status = "FINE"
                        else:
                            print(f"EMPTY:\t{sender}:\t{subject}")
                            status = "EMPTY"
                    
                    if only_gather_metrics:
                        metrics.append([status, sender, subject])
                    
                    processed_email_count += 1
                    #time.sleep(1/10) #throttle in seconds. 1/10 says process a max of 10 emails/second
            
            if processed_email_count >= max_email_count:
                print(f"DONE:\t{max_email_count} email processed.")
                break
        
        if not only_gather_metrics:
            mail.expunge()
    
    except Exception as e:
        print(f"An error occurred: {str(e)}")
    finally:
        mail.close()
        mail.logout()
    
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