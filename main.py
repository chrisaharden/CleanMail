import json
import imaplib
import email
from email.header import decode_header
import requests
import time

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

def is_spam(email_content, api_key):
    API_ENDPOINT = "https://api.anthropic.com/v1/messages"

    headers = {
        "Content-Type": "application/json",
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01"
    }

    # Limit email content to 500 characters
    limited_content = email_content[:500]

    data = {
        "model": "claude-3-opus-20240229",
        "max_tokens": 1000,
        "messages": [
            {"role": "user", "content": f"Is the following email spam? Only respond with 'yes' or 'no'. Here's the first 500 characters of the email: {limited_content}"}
        ]
    }

    try:
        response = requests.post(API_ENDPOINT, headers=headers, json=data)
        response.raise_for_status()
        
        ai_response = response.json()['content'][0]['text'].strip().lower()
        if ai_response not in ['yes', 'no']:
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

def process_emails(config, api_key):
    mail = imaplib.IMAP4_SSL(config['imap_server'], config['imap_port'])
    spam_count = 0
    whitelist = config.get('whitelist', [])
    blacklist = config.get('blacklist', [])
    only_gather_metrics = config.get('OnlyGatherMetrics', False)
    
    try:
        mail.login(config['email_address'], config['password'])
        mail.select('INBOX')
        
        _, message_numbers = mail.search(None, 'ALL')
        
        for num in message_numbers[0].split():
            _, msg = mail.fetch(num, '(RFC822)')
            
            for response in msg:
                if isinstance(response, tuple):
                    email_message = email.message_from_bytes(response[1])
                    subject = decode_email_subject(email_message["Subject"])
                    sender = email_message["From"]
                    
                    #print(f"Mail: {sender}: {subject}")
                    
                    # Check whitelist
                    if any(addr in sender for addr in whitelist):
                        print(f"WHITE:\t{sender}:\t{subject}")
                        continue
                    
                    # Check blacklist
                    if any(addr in sender for addr in blacklist):
                        print(f"BLACK:\t{sender}:\t{subject}")
                        if not only_gather_metrics:
                            try:
                                mail.copy(num, 'Junk')
                                mail.store(num, '+FLAGS', '\\Deleted')
                            except Exception as e:
                                print(f"Error moving email to Junk: {str(e)}")
                        spam_count += 1
                        continue
                    
                    content = get_email_content(email_message)
                    
                    if content:
                        if is_spam(content, api_key):
                            print(f"SPAM:\t{sender}:\t{subject}")
                            if not only_gather_metrics:
                                try:
                                    mail.copy(num, 'Junk')
                                    mail.store(num, '+FLAGS', '\\Deleted')
                                except Exception as e:
                                    print(f"Error moving email to Junk: {str(e)}")
                            spam_count += 1
                        else:
                            print(f"FINE:\t{sender}:\t{subject}")
                    else:
                        print(f"EMPTY:\t{sender}:\t{subject}")
                    
                    time.sleep(.25) #throttle
        
        if not only_gather_metrics:
            mail.expunge()
    
    except Exception as e:
        print(f"An error occurred: {str(e)}")
    finally:
        mail.close()
        mail.logout()
    
    return spam_count

if __name__ == "__main__":
    config = read_config('config.json')
    api_key = config.get('ANTHROPIC_API_KEY')
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY not found in config.json")
    total_spam = process_emails(config, api_key)
    print(f"Total {'potential' if config.get('OnlyGatherMetrics', False) else ''} emails {'that would be' if config.get('OnlyGatherMetrics', False) else ''} moved to Junk folder: {total_spam}")