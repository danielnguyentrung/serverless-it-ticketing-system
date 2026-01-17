# Serverless IT Ticketing System
A serverless IT Ticketing system built on AWS leveraging Amazon S3, API Gateway, SQS, Lambda, SNS, and SES for scalable request handling and notifications.

## Problem & Motivation

Many IT Teams spend a significant amount of time performing manual tasks. These include reviewing the content of each ticket to understand problem specifications and urgency, 
handling vague or incomplete ticket submissions, following up with users for missing information, and dealing with systems that are not providing concise ticket information. 

## Solution Overview

To address these challenges, I implemented a fully serverless IT ticketing system on AWS. The system automates ticket validation, prioritization, notifications, and duplicate detection, helping the IT team focus on resolving issues rather than manually managing tickets, while improving overall response times and reliability.

### Workflow

1. A user submits a support ticket through a static website hosted on Amazon S3.
2. The request is routed through Amazon API Gateway to an ingress AWS Lambda function, which validates the ticket contents.
3. Validated ticket metadata is sent to Amazon SQS to enable asynchronous processing and decouple ticket submission from downstream workflows.
4. A Lambda consumer processes messages from SQS, analyzes ticket content, determines urgency using a keyword-based grading metric, and detects duplicate tickets by querying DynamoDB using the user's email and ticket ID.
5. If the submitting user is not registered in the system, their information is queued for onboarding and added to DynamoDB.
6. Once the ticket has been processed, Amazon SNS is used to notify the IT team, and Amazon SES is used to notify end users.
7. Amazon EventBridge triggers a scheduled Lambda function to scan DynamoDB for tickets exceeding a seven-day threshold and notifies the IT team of stale tickets with full ticket details using SNS.

Note: Amazon CloudWatch is enabled to collect logs and metrics from all serverless components for monitoring and operational visibility. 

### Architecture Diagram

![Serverless Ticket Architecture](https://github.com/user-attachments/assets/53072b4b-a55a-4339-9b4e-3172bd5bbc05)

### Ticket Submission Interface

The ticket submission interface is deployed as a static website on Amazon S3: 

[View Live Website](https://it-ticket-portal.s3.us-east-2.amazonaws.com/index.html)

<img width="1902" height="940" alt="image" src="https://github.com/user-attachments/assets/94a94bf4-20bf-4f2b-a05b-9b1df6f5016d" />

## Lessons Learned

