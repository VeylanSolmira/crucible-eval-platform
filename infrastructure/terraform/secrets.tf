# AWS Secrets Manager for sensitive configuration

# Random password generation for database
resource "random_password" "db_password" {
  length  = 32
  special = true
  # Exclude problematic characters for URLs and shell commands
  override_special = "!#$%&*()-_=+[]{}:?"
}

# Store database password in Secrets Manager
resource "aws_secretsmanager_secret" "db_password" {
  name                    = "${var.project_name}/db-password"
  description             = "PostgreSQL password for Crucible platform"
  recovery_window_in_days = 7 # Keep deleted secrets for 7 days

  tags = merge(local.common_tags, {
    Name    = "${var.project_name}-db-password"
    Purpose = "Database credentials"
  })
}

resource "aws_secretsmanager_secret_version" "db_password" {
  secret_id     = aws_secretsmanager_secret.db_password.id
  secret_string = random_password.db_password.result
}

# IAM policy to allow EC2 instances to read the secret
resource "aws_iam_role_policy" "eval_server_secrets" {
  name = "crucible-eval-server-secrets-policy"
  role = aws_iam_role.eval_server.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "secretsmanager:GetSecretValue",
          "secretsmanager:DescribeSecret"
        ]
        Resource = [
          aws_secretsmanager_secret.db_password.arn
        ]
      }
    ]
  })
}

# IAM policy to allow GitHub Actions to read the secret
resource "aws_iam_role_policy" "github_actions_secrets" {
  name = "crucible-github-actions-secrets-policy"
  role = aws_iam_role.github_actions.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "secretsmanager:GetSecretValue",
          "secretsmanager:DescribeSecret"
        ]
        Resource = [
          aws_secretsmanager_secret.db_password.arn
        ]
      }
    ]
  })
}

# Output the secret ARN for reference
output "db_password_secret_arn" {
  description = "ARN of the database password secret"
  value       = aws_secretsmanager_secret.db_password.arn
}

output "db_password_secret_name" {
  description = "Name of the database password secret"
  value       = aws_secretsmanager_secret.db_password.name
}