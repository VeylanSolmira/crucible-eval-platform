"""
Lambda handler for evaluation submission API
"""

import json
import os
import uuid
from datetime import datetime, timezone
import boto3

sqs = boto3.client("sqs")
QUEUE_URL = os.environ["QUEUE_URL"]


def submit_evaluation(event, context):
    """
    Handle POST /evaluations
    Validates request and enqueues evaluation task
    """
    try:
        # Parse request body
        body = json.loads(event["body"])

        # Basic validation
        if "script" not in body:
            return {"statusCode": 400, "body": json.dumps({"error": "Script is required"})}

        # Quick safety check (basic patterns)
        script = body["script"]
        if any(danger in script for danger in ["import os", "import subprocess", "__import__"]):
            return {
                "statusCode": 403,
                "body": json.dumps({"error": "Potentially unsafe code detected"}),
            }

        # Generate evaluation ID
        evaluation_id = f"eval-{uuid.uuid4()}"

        # Prepare task message
        task = {
            "evaluation_id": evaluation_id,
            "script": script,
            "model_id": body.get("model_id", "default"),
            "submitted_at": datetime.now(timezone.utc).isoformat(),
            "status": "queued",
        }

        # Send to SQS
        sqs.send_message(QueueUrl=QUEUE_URL, MessageBody=json.dumps(task))

        # Return success response
        return {
            "statusCode": 202,
            "body": json.dumps(
                {
                    "evaluation_id": evaluation_id,
                    "status": "queued",
                    "message": "Evaluation submitted successfully",
                }
            ),
        }

    except Exception as e:
        print(f"Error: {str(e)}")
        return {"statusCode": 500, "body": json.dumps({"error": "Internal server error"})}
