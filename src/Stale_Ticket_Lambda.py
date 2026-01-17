import boto3
import json
import os
import time 


dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table(os.environ["USERS_TABLE"])
sns = boto3.client('sns')
SNS_TOPIC_ARN = os.environ["SNS_TOPIC_ARN"]

def stale_ticket_checker():
    response = table.scan()
    users = response.get('Items', [])

    current_time = int(time.time())
    stale_threshold = 7 * 24 * 60 * 60

    stale_tickets = [] 

    for user in users: 
        email = user.get("email")
        tickets = user.get("ticket_ids", [])
        updated = False 

        for ticket in tickets:
                if ticket.get("status") != "OPEN":
                     continue 
                
                created_at = ticket.get('created_at')
                if not created_at:
                     continue 
                
                ticket_age = current_time - created_at

                if ticket_age > stale_threshold:
                    ticket['status'] = "STALE"
                    updated = True 

                    stale_tickets.append({
                         "ticket_id": ticket.get("ticket_id"),
                         "ticket_title": ticket.get("ticket_title"),
                         "email": email, 
                         "age_days": ticket_age // 86400, 
                         "created_at": created_at
                    })
    
        if updated:
             table.update_item(
                Key={"email": email},
                UpdateExpression="SET ticket_ids = :tickets", 
                ExpressionAttributeValues={":tickets": tickets}
            )
    return stale_tickets

def send_to_sns(message, subject): 

    try:
        response = sns.publish(
            TopicArn = SNS_TOPIC_ARN,
            Message = json.dumps(message),
            Subject=subject
        )
         
        print("SNS message sent:"), response['MessageId']

    except Exception as e:
        print("Error sending SNS message", e)
        
def lambda_handler(event, context):
    stale_tickets = stale_ticket_checker()

    if stale_tickets:
        send_to_sns(stale_tickets, subject="Stale Ticket Alert")
    
    return{"statusCode": 200,
           "body": json.dumps({
                "stale_tickets_processed": "Stale ticket count successfully completed."
           })}

    

