# queue.tf - SQS queue for evaluation tasks

resource "aws_sqs_queue" "evaluation_queue" {
  name                       = "metr-evaluation-queue-${var.environment}"
  delay_seconds              = 0
  max_message_size           = 262144  # 256 KB
  message_retention_seconds  = 86400   # 1 day
  receive_wait_time_seconds  = 20      # Long polling
  visibility_timeout_seconds = 300     # 5 minutes for processing

  # Enable server-side encryption
  sqs_managed_sse_enabled = true

  tags = {
    Project     = "metr-eval-platform"
    Environment = var.environment
  }
}

# Dead letter queue for failed messages
resource "aws_sqs_queue" "evaluation_dlq" {
  name                      = "metr-evaluation-dlq-${var.environment}"
  message_retention_seconds = 1209600  # 14 days

  sqs_managed_sse_enabled = true

  tags = {
    Project     = "metr-eval-platform"
    Environment = var.environment
  }
}

# Configure main queue to use DLQ
resource "aws_sqs_queue_redrive_policy" "evaluation_queue" {
  queue_url = aws_sqs_queue.evaluation_queue.id
  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.evaluation_dlq.arn
    maxReceiveCount     = 3
  })
}