# api.tf - API Gateway and Lambda for evaluation submission

# Package Lambda code from src directory
data "archive_file" "lambda_zip" {
  type        = "zip"
  source_dir  = "../../src/lambda"
  output_path = "lambda_deployment.zip"
}

# Lambda function for handling evaluation requests
resource "aws_lambda_function" "evaluation_handler" {
  filename         = data.archive_file.lambda_zip.output_path
  function_name    = "metr-evaluation-handler"
  role            = aws_iam_role.lambda_role.arn
  handler         = "handler.submit_evaluation"
  runtime         = "python3.11"
  timeout         = 30
  memory_size     = 512
  source_code_hash = data.archive_file.lambda_zip.output_base64sha256

  environment {
    variables = {
      QUEUE_URL = aws_sqs_queue.evaluation_queue.url
      STAGE     = var.environment
    }
  }

  tags = {
    Project     = "metr-eval-platform"
    Environment = var.environment
  }
}

# IAM role for Lambda
resource "aws_iam_role" "lambda_role" {
  name = "metr-evaluation-lambda-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
      }
    ]
  })
}

# Lambda permissions - basic execution + SQS write
resource "aws_iam_role_policy_attachment" "lambda_basic" {
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
  role       = aws_iam_role.lambda_role.name
}

resource "aws_iam_role_policy" "lambda_sqs" {
  name = "lambda-sqs-policy"
  role = aws_iam_role.lambda_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "sqs:SendMessage",
          "sqs:GetQueueAttributes"
        ]
        Resource = aws_sqs_queue.evaluation_queue.arn
      }
    ]
  })
}

# API Gateway REST API
resource "aws_api_gateway_rest_api" "evaluation_api" {
  name        = "metr-evaluation-api"
  description = "API for submitting AI model evaluations"

  endpoint_configuration {
    types = ["REGIONAL"]
  }
}

# API Gateway resource for /evaluations
resource "aws_api_gateway_resource" "evaluations" {
  rest_api_id = aws_api_gateway_rest_api.evaluation_api.id
  parent_id   = aws_api_gateway_rest_api.evaluation_api.root_resource_id
  path_part   = "evaluations"
}

# POST method
resource "aws_api_gateway_method" "post_evaluation" {
  rest_api_id   = aws_api_gateway_rest_api.evaluation_api.id
  resource_id   = aws_api_gateway_resource.evaluations.id
  http_method   = "POST"
  authorization = "NONE"  # Add API key or Cognito later
}

# Lambda integration
resource "aws_api_gateway_integration" "lambda_integration" {
  rest_api_id = aws_api_gateway_rest_api.evaluation_api.id
  resource_id = aws_api_gateway_resource.evaluations.id
  http_method = aws_api_gateway_method.post_evaluation.http_method

  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = aws_lambda_function.evaluation_handler.invoke_arn
}

# Lambda permission for API Gateway
resource "aws_lambda_permission" "api_gateway" {
  statement_id  = "AllowAPIGatewayInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.evaluation_handler.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_api_gateway_rest_api.evaluation_api.execution_arn}/*/*"
}

# Deploy API
resource "aws_api_gateway_deployment" "evaluation_api" {
  depends_on = [
    aws_api_gateway_integration.lambda_integration
  ]

  rest_api_id = aws_api_gateway_rest_api.evaluation_api.id
}

# Create API stage
resource "aws_api_gateway_stage" "evaluation_api" {
  deployment_id = aws_api_gateway_deployment.evaluation_api.id
  rest_api_id   = aws_api_gateway_rest_api.evaluation_api.id
  stage_name    = var.environment
}

# Output the API endpoint
output "api_endpoint" {
  value = "https://${aws_api_gateway_rest_api.evaluation_api.id}.execute-api.${var.aws_region}.amazonaws.com/${var.environment}/evaluations"
}