import json
import re
import boto3
from datetime import datetime
import uuid
import time
import os

sqs = boto3.client("sqs")
QueueUrl = os.environ["QUEUE_URL"]

CORS_HEADERS = {
    "Access-Control-Allow-Origin": "https://it-ticket-portal.s3.us-east-2.amazonaws.com",  # exact origin
    "Access-Control-Allow-Headers": "Content-Type",
    "Access-Control-Allow-Methods": "POST,OPTIONS",
    "Access-Control-Allow-Credentials": "false"  # only needed if no cookies or auth
}

def ticket_generator():
    date_part = datetime.utcnow().strftime("%d-%m-%Y")
    unique_part = uuid.uuid4().hex[:4]

    return f"Ticket-{date_part}-{unique_part}"
     

def validate_required_fields(body): 
    required_fields = [
        "first_name",
        "last_name", 
        "email", 
        "ticket_title", 
        "problem_type", 
        "ticket_description"
    ]

    for field in required_fields:
        if field not in body or not str(body[field]).strip():
            raise ValueError(f"Missing required field: {field}")
        
def validate_name(value): 
        name_pattern = r"^[A-Za-zÀ-ÖØ-öø-ÿ' \-]+$"
        if not re.fullmatch(name_pattern, value):
            raise ValueError("Invalid Name")
    
def validate_email(value):
        email_pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        if not re.fullmatch(email_pattern, value):
            raise ValueError("Invalid Email")
    
def validate_word_count(value, max_words, field_name = "Field"):
        word_count = len(value.split())
        if word_count > max_words:
            raise ValueError(f"{field_name} exceeds {max_words} words")
    
def validate_problem_type(value):
    valid_problems = [
        "account", 
        "hardware", 
        "software", 
        "network/connectivity",
        "security",
        "mobile",
        "service",
        "other/miscellaneous"
    ]
    if value.lower() not in valid_problems:
        raise ValueError("Invalid Problem Type")

def validate_character_count(value, max_chars):
    if len(value) > max_chars:
        raise ValueError(f"Description exceeds {max_chars} characters")
    
def lambda_handler(event, context):
    method = (event.get("requestContext", {}).get("http", {}).get("method") 
        or event.get("httpMethod")
        or "")

    if method == "OPTIONS":
        return {
             "statusCode": 200, 
             "headers": CORS_HEADERS,
             "body": ""
        }
    if "body" not in event or not event["body"]:
        return {
            "statusCode": 400,
            "headers": CORS_HEADERS,
            "body": json.dumps({"error": "Missing request body"})
        }
    
    try:
        body = json.loads(event["body"])

        validate_required_fields(body)
        validate_name(body["first_name"])
        validate_name(body["last_name"])
        validate_email(body["email"])
        validate_word_count(body["ticket_title"], 10, "Ticket title")
        validate_problem_type(body["problem_type"])
        validate_character_count(body["ticket_description"], 500)

        creation_at = int(time.time()) 
        
        sqs.send_message(
        QueueUrl = QueueUrl,
        MessageBody=json.dumps({
            "first_name": body["first_name"], 
            "last_name": body["last_name"], 
            "ticket_id": ticket_generator(),
            "email": body["email"], 
            "ticket_title": body["ticket_title"], 
            "problem_type": body["problem_type"],
            "ticket_description": body["ticket_description"],   
            "created_at": creation_at})    
        )
        return {
            'statusCode': 200,
            'headers': CORS_HEADERS,
            'body': json.dumps({"message": "Ticket validated and sent to the queue successfully"})
        }
    
    except ValueError as e:
        return {
            'statusCode': 400,
            'headers': CORS_HEADERS,
            'body': json.dumps({"error": str(e)})
        }
    
    except json.JSONDecodeError:
        return {
            'statusCode': 400,
            'headers': CORS_HEADERS,
            'body': json.dumps({"error": "Invalid JSON in request body"})
        }
        