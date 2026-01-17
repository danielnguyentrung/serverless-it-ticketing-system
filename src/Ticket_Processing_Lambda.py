import json
import boto3
import os
import time
import re
import textwrap 

dynamodb = boto3.resource('dynamodb')
table_name = os.environ['USERS_TABLE']
table = dynamodb.Table(table_name)
sns = boto3.client('sns')
SNS_TOPIC_ARN = os.environ['SNS_TOPIC_ARN']
ses = boto3.client('ses')
SENDER_EMAIL = os.environ['SENDER_EMAIL']

keyword_weight = {
    # High Severity
    "data loss": 100,
    "system down": 100,
    "server down": 100,
    "fatal": 100,
    "virus": 100,
    "outage": 100,
    "failure": 100,
    "system error": 60,
    
    # Medium-High Severity
    "clients affected": 50,
    "critical": 50,
    "urgent": 50,
    
    # Medium Severity
    "offline": 20,
    "effective immediately": 20,
    "spam": 20,
    "some users": 15,
    "end of day": 15,
    "lock out": 15,
    "lockout": 15,
    "password": 15,
    "vpn": 15,
    "locked out": 15,
    "phishing": 15,
    
    # Low-Medium Severity
    "not working": 10,
    "terminate": 10,
    "disable": 10,
    "error": 10,
    "minor bug": 10,
    "bug": 10,
    "update": 10,
    "login": 10,
    
    # Low Severity
    "question": 5,
    "reset": 5,
    "slow": 5,
    "not opening": 5,
    "new hire": 5,
    "hire": 5,
    "onboarding": 5,
    "set-up": 5,
    "set up": 5,
    "print": 5,
    "printing": 5,
    "printer": 5,
    "email": 5,
    "new": 5,
    "install": 5,
    "how do i": 5,
    "request": 5,
    "order": 5
}


def add_ticket(body):
    email = body.get('email')
    ticket_id = body.get('ticket_id')
    created_at = body.get('created_at', int(time.time()))

    if not email or not ticket_id:
        raise ValueError("Missing email or ticket_id")

    ticket_data = {
        "ticket_id": ticket_id,
        "ticket_title": body.get('ticket_title'),
        "ticket_description": body.get('ticket_description'),
        "problem_type": body.get('problem_type'),
        "status": "OPEN",
        "created_at": created_at
    }
    
    response = table.get_item(Key={'email': email})
    user_tickets = response.get('Item', {}).get('ticket_ids', [])

    if any(ticket['ticket_id'] == ticket_id for ticket in user_tickets):
        print(f"Ticket {ticket_id} already exists for email {email}.")
        return 
    
    user_tickets.append(ticket_data)

    table.update_item(
        Key={'email': email},
        UpdateExpression="SET ticket_ids = :tickets",
        ExpressionAttributeValues={':tickets': user_tickets}
    )

    print(f"Ticket {ticket_id} added for email {email}.")

def email_check(body):
    email = body.get('email')
    first_name = body.get('first_name')
    last_name = body.get('last_name')

    if not email:
        raise ValueError("Missing email")

    response = table.get_item(
        Key={'email': email})

    if "Item" not in response:
        table.put_item(
            Item={
                'email': email, 
                'first_name': first_name,
                'last_name': last_name,
                'ticket_ids': []
            }
        )
    else:
        print(f"Email: {email} is already registered to an account.")


def ticket_urgency(body):
    title = body.get('ticket_title', '')
    ticket_description = body.get('ticket_description', '')
    if not ticket_description or not title:
        return{"urgency": 1}

    title_lower = title.lower()
    ticket_description_lower = ticket_description.lower() 

    matched_title_keywords = set()
    matched_description_keywords = set()
    
    for keyword, score in keyword_weight.items():
        pattern = rf'\b{re.escape(keyword)}\b'
 
        if re.search(pattern, title_lower): 
            matched_title_keywords.add(keyword)
        
        if re.search(pattern, ticket_description_lower):
            matched_description_keywords.add(keyword)

    title_score = sum(keyword_weight[value] for value in matched_title_keywords)
    description_score = sum(keyword_weight[value] for value in matched_description_keywords)
        
    combined_score = title_score + (description_score / 2)
        
    if combined_score >= 100:
        urgency = 5
    elif combined_score >= 80:
        urgency = 4
    elif combined_score >= 60:
        urgency = 3
    elif combined_score >= 40:
        urgency = 2
    else: 
        urgency = 1
    
    return {"urgency": urgency}


def process_ticket(body):
    email_check(body)
    add_ticket(body)

def send_to_sns(message, subject):

    try: 
        response = sns.publish(
            TopicArn=SNS_TOPIC_ARN, 
            Message=message,
            Subject=subject
        )
        
        print("SNS message sent:", response['MessageId'])
    except Exception as e: 
        print("Error sending SNS message:", e)

def send_client_email(to_email, subject, body):
    try:
        response = ses.send_email(
            Source=SENDER_EMAIL,
            Destination={
                "ToAddresses": [to_email]
            },
            Message={
                "Subject": {
                    "Data": subject,
                    "Charset": "UTF-8"
                },
                "Body": {
                    "Text": {
                        "Data": body,
                        "Charset": "UTF-8"
                    }
                }
            }
        )
        print("SES email sent:", response["MessageId"])
        return True
    except Exception as e:
        print("SES email failed:", e)
        return False

def lambda_handler(event, context):

    for record in event['Records']:
        body = json.loads(record['body'])
        process_ticket(body)
        urgency = ticket_urgency(body)
    

        it_message = textwrap.dedent(f"""
        Hi Team, 

        Please review the IT Ticket. 

        Ticket Summary: 
        Name: {body.get('first_name')} {body.get('last_name')}
        Email: {body.get('email')}
        Ticket ID: {body.get('ticket_id')}
        Title: {body.get('ticket_title')}
        Ticket Description: {body.get('ticket_description')}
        Urgency: {urgency['urgency']}

        Thank you,
        Daniel 
        """).strip()

        client_message = textwrap.dedent(f"""
        Hi {body.get('first_name')}, 

        Your IT ticket has been submitted successfully. 

        Ticket Summary:
        Ticket ID: {body.get('ticket_id')}
        Title: {body.get('ticket_title')}
        Ticket Description: {body.get('ticket_description')}
        Urgency: {urgency['urgency']}
    
        Please allow for 24 hours for our team to review the ticket. We will notify you once it has been resolved. 

        Thank you,
        Daniel's IT Support Team 
        """).strip()

        send_to_sns(it_message, subject="New IT Ticket")
        send_client_email(body.get('email'), subject="Your IT Ticket has been submitted", body=client_message)


    

