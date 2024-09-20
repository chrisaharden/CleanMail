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

    data = {
        "model": "claude-3-opus-20240229",
        "max_tokens": 1000,
        "messages": [
            {"role": "user", "content": f"Is the following email spam? Only respond with 'yes' or 'no'. Here's the email: {email_content}"}
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
                    
                    content = get_email_content(email_message)
                    
                    print(f"Processing email: {subject}")
                    print(f"Content length: {len(content)} characters")
                    
                    if content:
                        if is_spam(content, api_key):
                            print(f"Moving to Junk: {subject}")
                            #HARDEN mail.copy(num, 'Junk')
                            #HARDEN mail.store(num, '+FLAGS', '\\Deleted')
                            spam_count += 1
                        else:
                            print(f"Not spam: {subject}")
                    else:
                        print(f"Warning: Empty content for email: {subject}")
                    
                    time.sleep(2)
        
        mail.expunge()
    
    finally:
        mail.close()
        mail.logout()
    
    return spam_count

if __name__ == "__main__":
    config = read_config('config.json')
    api_key = config.get('ANTHROPIC_API_KEY')
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY not found in configimap.json")
    total_spam = process_emails(config, api_key)
    print(f"Total emails moved to Junk folder: {total_spam}")