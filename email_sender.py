# email_sender.py
import os
import base64
import mimetypes
from email.message import EmailMessage
from googleapiclient.discovery import build

def create_message(sender, to, subject, body, attachment_paths=None):
    """
    Creates an email message object.
    Includes robust binary file handling to prevent attachment corruption.
    """
    message = EmailMessage()
    message.set_content(body)
    message['To'] = to
    message['From'] = sender
    message['Subject'] = subject

    if attachment_paths and isinstance(attachment_paths, list):
        for path in attachment_paths:
            if os.path.exists(path):
                # 1. Guess the MIME type
                ctype, encoding = mimetypes.guess_type(path)
                
                # 2. Handle cases where guess fails or file is encoded
                if ctype is None or encoding is not None:
                    # Default to generic binary stream to ensure safety
                    ctype = 'application/octet-stream'
                
                maintype, subtype = ctype.split('/', 1)
                
                try:
                    # 3. CRITICAL: Open in 'rb' (Read Binary) mode
                    with open(path, 'rb') as fp:
                        file_data = fp.read()
                        
                        # 4. Attach with correct headers
                        message.add_attachment(
                            file_data,
                            maintype=maintype,
                            subtype=subtype,
                            filename=os.path.basename(path)
                        )
                        print(f"Attached file: {path} as {maintype}/{subtype}")
                except Exception as e:
                    print(f"Error attaching file {path}: {e}")
            else:
                print(f"Warning: Attachment not found at {path}")

    return message

def send_email(credentials, recipient_emails, subject, body, attachment_paths=None):
    """
    Sends an email using the user's Gmail account via the Gmail API.
    """
    try:
        service = build('gmail', 'v1', credentials=credentials, cache_discovery=False)
        
        # Get the user's own email address
        profile = service.users().getProfile(userId='me').execute()
        user_email = profile.get('emailAddress')
        
        if not isinstance(recipient_emails, list):
            recipient_emails = [recipient_emails]
        
        # Create the email object
        email_message = create_message(user_email, ", ".join(recipient_emails), subject, body, attachment_paths)
        
        # Encode the message (Base64URL) required by Gmail API
        encoded_message = base64.urlsafe_b64encode(email_message.as_bytes()).decode()
        create_message_body = {'raw': encoded_message}
        
        # Send the email
        sent_message = service.users().messages().send(userId="me", body=create_message_body).execute()
        
        recipient_str = ", ".join(recipient_emails)
        confirmation = f"✅ Email successfully sent to {recipient_str}!"
        if attachment_paths:
             confirmation += f"\n📎 Attachments: {len(attachment_paths)}"
             
        return confirmation

    except Exception as e:
        print(f"Gmail API sending error: {e}")
        return f"❌ Failed to send email: {str(e)}"
