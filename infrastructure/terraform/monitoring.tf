# monitoring.tf - CloudWatch monitoring and alerting for Crucible Platform

locals {
  # Construct the full alert email with suffix for filtering
  alert_email = var.alert_email_base != "" ? "${split("@", var.alert_email_base)[0]}+${var.alert_email_suffix}@${split("@", var.alert_email_base)[1]}" : ""
}

# SNS Topic for Alerts
resource "aws_sns_topic" "crucible_alerts" {
  name = "${var.project_name}-alerts"
  
  tags = merge(var.common_tags, {
    Name = "${var.project_name}-alerts"
  })
}

resource "aws_sns_topic_subscription" "crucible_alerts_email" {
  count     = local.alert_email != "" ? 1 : 0
  topic_arn = aws_sns_topic.crucible_alerts.arn
  protocol  = "email"
  endpoint  = local.alert_email
}

# CloudWatch Log Groups
resource "aws_cloudwatch_log_group" "crucible_docker" {
  name              = "/aws/ec2/${var.project_name}/docker"
  retention_in_days = 7
  
  tags = merge(var.common_tags, {
    Name = "${var.project_name}-docker-logs"
  })
}

resource "aws_cloudwatch_log_group" "crucible_system" {
  name              = "/aws/ec2/${var.project_name}/system"
  retention_in_days = 7
  
  tags = merge(var.common_tags, {
    Name = "${var.project_name}-system-logs"
  })
}

# CloudWatch Agent Configuration
resource "aws_ssm_parameter" "cloudwatch_agent_config" {
  name  = "/${var.project_name}/cloudwatch-agent/config"
  type  = "String"
  value = jsonencode({
    agent = {
      metrics_collection_interval = 60
      run_as_user                 = "cwagent"
    }
    metrics = {
      namespace = "${var.project_name}/System"
      metrics_collected = {
        cpu = {
          measurement = [
            {
              name = "cpu_usage_idle"
              rename = "CPU_USAGE_IDLE"
              unit = "Percent"
            },
            {
              name = "cpu_usage_iowait"
              rename = "CPU_USAGE_IOWAIT"
              unit = "Percent"
            },
            "cpu_time_guest"
          ]
          totalcpu = false
          metrics_collection_interval = 60
        }
        disk = {
          measurement = [
            "used_percent",
            "inodes_free"
          ]
          metrics_collection_interval = 60
          resources = [
            "*"
          ]
        }
        diskio = {
          measurement = [
            "io_time"
          ]
          metrics_collection_interval = 60
          resources = [
            "*"
          ]
        }
        mem = {
          measurement = [
            "mem_used_percent",
            "mem_available",
            "mem_used",
            "mem_total"
          ]
          metrics_collection_interval = 60
        }
        netstat = {
          measurement = [
            "tcp_established",
            "tcp_time_wait"
          ]
          metrics_collection_interval = 60
        }
        swap = {
          measurement = [
            "swap_used_percent",
            "swap_free",
            "swap_used"
          ]
          metrics_collection_interval = 60
        }
      }
    }
    logs = {
      logs_collected = {
        files = {
          collect_list = [
            {
              file_path = "/var/log/docker/**/*.log"
              log_group_name = "/aws/ec2/${var.project_name}/docker"
              log_stream_name = "{instance_id}/{container_name}"
              timezone = "UTC"
            },
            {
              file_path = "/var/log/syslog"
              log_group_name = "/aws/ec2/${var.project_name}/system"
              log_stream_name = "{instance_id}/syslog"
              timezone = "UTC"
            },
            {
              file_path = "/var/log/messages"
              log_group_name = "/aws/ec2/${var.project_name}/system"
              log_stream_name = "{instance_id}/messages"
              timezone = "UTC"
            }
          ]
        }
      }
    }
  })
  
  tags = merge(var.common_tags, {
    Name = "${var.project_name}-cloudwatch-config"
  })
}

# Log Metric Filters for Container Issues

# OOM Kill Detection
resource "aws_cloudwatch_log_metric_filter" "oom_kills" {
  name           = "${var.project_name}-oom-kills"
  log_group_name = aws_cloudwatch_log_group.crucible_docker.name
  pattern        = "[time, id, level, component, msg = \"*OOMKilled*\" || msg = \"*memory limit*\" || msg = \"*out of memory*\"]"
  
  metric_transformation {
    name          = "OOMKillCount"
    namespace     = "${var.project_name}/Containers"
    value         = "1"
    default_value = "0"
  }
}

# Container Restart Detection
resource "aws_cloudwatch_log_metric_filter" "container_restarts" {
  name           = "${var.project_name}-container-restarts"
  log_group_name = aws_cloudwatch_log_group.crucible_docker.name
  pattern        = "[time, id, level, component, msg = \"*container die*\" || msg = \"*restarting*\"]"
  
  metric_transformation {
    name          = "ContainerRestartCount"
    namespace     = "${var.project_name}/Containers"
    value         = "1"
    default_value = "0"
  }
}

# Container Failed to Start
resource "aws_cloudwatch_log_metric_filter" "container_start_failures" {
  name           = "${var.project_name}-container-start-failures"
  log_group_name = aws_cloudwatch_log_group.crucible_docker.name
  pattern        = "[time, id, level, component, msg = \"*failed to start*\" || msg = \"*error creating container*\"]"
  
  metric_transformation {
    name          = "ContainerStartFailureCount"
    namespace     = "${var.project_name}/Containers"
    value         = "1"
    default_value = "0"
  }
}

# Docker Daemon Errors
resource "aws_cloudwatch_log_metric_filter" "docker_errors" {
  name           = "${var.project_name}-docker-errors"
  log_group_name = aws_cloudwatch_log_group.crucible_system.name
  pattern        = "[time, id, level = ERROR, component = docker*, ...]"
  
  metric_transformation {
    name          = "DockerErrorCount"
    namespace     = "${var.project_name}/System"
    value         = "1"
    default_value = "0"
  }
}

# Alarms

# OOM Kill Alarm
resource "aws_cloudwatch_metric_alarm" "oom_alarm" {
  alarm_name          = "${var.project_name}-oom-kills"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "1"
  metric_name         = "OOMKillCount"
  namespace           = "${var.project_name}/Containers"
  period              = "300"
  statistic           = "Sum"
  threshold           = "0"
  alarm_description   = "Container OOM kills detected in ${var.project_name}"
  treat_missing_data  = "notBreaching"
  alarm_actions       = [aws_sns_topic.crucible_alerts.arn]
  
  tags = merge(var.common_tags, {
    Name = "${var.project_name}-oom-alarm"
  })
}

# Container Restart Alarm (more than 5 in 15 minutes)
resource "aws_cloudwatch_metric_alarm" "container_restart_alarm" {
  alarm_name          = "${var.project_name}-container-restarts"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "1"
  metric_name         = "ContainerRestartCount"
  namespace           = "${var.project_name}/Containers"
  period              = "900"
  statistic           = "Sum"
  threshold           = "5"
  alarm_description   = "Multiple container restarts detected in ${var.project_name}"
  treat_missing_data  = "notBreaching"
  alarm_actions       = [aws_sns_topic.crucible_alerts.arn]
  
  tags = merge(var.common_tags, {
    Name = "${var.project_name}-restart-alarm"
  })
}

# Low Available Memory Alarm (not percentage-based)
resource "aws_cloudwatch_metric_alarm" "low_memory_alarm" {
  alarm_name          = "${var.project_name}-low-available-memory"
  comparison_operator = "LessThanThreshold"
  evaluation_periods  = "3"
  metric_name         = "mem_available"
  namespace           = "${var.project_name}/System"
  period              = "60"
  statistic           = "Average"
  threshold           = "104857600"  # 100MB in bytes
  alarm_description   = "Available memory below 100MB in ${var.project_name}"
  treat_missing_data  = "breaching"
  alarm_actions       = [aws_sns_topic.crucible_alerts.arn]
  
  tags = merge(var.common_tags, {
    Name = "${var.project_name}-low-memory-alarm"
  })
}

# High Memory Pressure Alarm (sustained high usage)
resource "aws_cloudwatch_metric_alarm" "memory_pressure_alarm" {
  alarm_name          = "${var.project_name}-memory-pressure"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "5"
  metric_name         = "mem_used_percent"
  namespace           = "${var.project_name}/System"
  period              = "60"
  statistic           = "Average"
  threshold           = "95"
  alarm_description   = "Sustained high memory usage (>95%) in ${var.project_name}"
  treat_missing_data  = "breaching"
  alarm_actions       = [aws_sns_topic.crucible_alerts.arn]
  
  tags = merge(var.common_tags, {
    Name = "${var.project_name}-memory-pressure-alarm"
  })
}

# High Swap Usage Alarm
resource "aws_cloudwatch_metric_alarm" "swap_usage_alarm" {
  alarm_name          = "${var.project_name}-high-swap-usage"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "3"
  metric_name         = "swap_used_percent"
  namespace           = "${var.project_name}/System"
  period              = "300"
  statistic           = "Average"
  threshold           = "25"
  alarm_description   = "High swap usage detected in ${var.project_name}"
  treat_missing_data  = "notBreaching"
  alarm_actions       = [aws_sns_topic.crucible_alerts.arn]
  
  tags = merge(var.common_tags, {
    Name = "${var.project_name}-swap-alarm"
  })
}

# Container Start Failure Alarm
resource "aws_cloudwatch_metric_alarm" "container_start_failure_alarm" {
  alarm_name          = "${var.project_name}-container-start-failures"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "1"
  metric_name         = "ContainerStartFailureCount"
  namespace           = "${var.project_name}/Containers"
  period              = "300"
  statistic           = "Sum"
  threshold           = "0"
  alarm_description   = "Container failed to start in ${var.project_name}"
  treat_missing_data  = "notBreaching"
  alarm_actions       = [aws_sns_topic.crucible_alerts.arn]
  
  tags = merge(var.common_tags, {
    Name = "${var.project_name}-start-failure-alarm"
  })
}

# API Health Check via HTTP endpoint check
# Note: Since we're not using ALB, this could be replaced with a Route53 health check
# or a Lambda-based health checker in the future

# Disk Usage Alarm
resource "aws_cloudwatch_metric_alarm" "disk_usage_alarm" {
  alarm_name          = "${var.project_name}-high-disk-usage"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "disk_used_percent"
  namespace           = "${var.project_name}/System"
  period              = "300"
  statistic           = "Average"
  threshold           = "85"
  alarm_description   = "High disk usage (>85%) in ${var.project_name}"
  treat_missing_data  = "breaching"
  alarm_actions       = [aws_sns_topic.crucible_alerts.arn]
  
  dimensions = {
    device = "xvda1"
    fstype = "ext4"
    path   = "/"
  }
  
  tags = merge(var.common_tags, {
    Name = "${var.project_name}-disk-alarm"
  })
}

# Docker Daemon Error Alarm
resource "aws_cloudwatch_metric_alarm" "docker_error_alarm" {
  alarm_name          = "${var.project_name}-docker-errors"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "1"
  metric_name         = "DockerErrorCount"
  namespace           = "${var.project_name}/System"
  period              = "300"
  statistic           = "Sum"
  threshold           = "5"
  alarm_description   = "Multiple Docker daemon errors in ${var.project_name}"
  treat_missing_data  = "notBreaching"
  alarm_actions       = [aws_sns_topic.crucible_alerts.arn]
  
  tags = merge(var.common_tags, {
    Name = "${var.project_name}-docker-error-alarm"
  })
}

# CloudWatch Dashboard
resource "aws_cloudwatch_dashboard" "crucible_monitoring" {
  dashboard_name = "${var.project_name}-monitoring"
  
  dashboard_body = jsonencode({
    widgets = [
      {
        type   = "metric"
        x      = 0
        y      = 0
        width  = 12
        height = 6
        properties = {
          metrics = [
            ["${var.project_name}/System", "mem_used_percent", { stat = "Average" }],
            [".", "mem_available", { stat = "Average", yAxis = "right" }]
          ]
          period = 300
          stat   = "Average"
          region = var.aws_region
          title  = "Memory Usage"
          yAxis = {
            left = {
              min = 0
              max = 100
            }
            right = {
              min = 0
            }
          }
        }
      },
      {
        type   = "metric"
        x      = 12
        y      = 0
        width  = 12
        height = 6
        properties = {
          metrics = [
            ["${var.project_name}/Containers", "OOMKillCount", { stat = "Sum" }],
            [".", "ContainerRestartCount", { stat = "Sum" }],
            [".", "ContainerStartFailureCount", { stat = "Sum" }]
          ]
          period = 300
          stat   = "Sum"
          region = var.aws_region
          title  = "Container Issues"
          yAxis = {
            left = {
              min = 0
            }
          }
        }
      },
      {
        type   = "metric"
        x      = 0
        y      = 6
        width  = 12
        height = 6
        properties = {
          metrics = [
            ["AWS/EC2", "CPUUtilization", { stat = "Average" }]
          ]
          period = 300
          stat   = "Average"
          region = var.aws_region
          title  = "CPU Usage"
          yAxis = {
            left = {
              min = 0
              max = 100
            }
          }
        }
      },
      {
        type   = "metric"
        x      = 12
        y      = 6
        width  = 12
        height = 6
        properties = {
          metrics = [
            ["${var.project_name}/System", "disk_used_percent", { stat = "Average" }],
            [".", "swap_used_percent", { stat = "Average" }]
          ]
          period = 300
          stat   = "Average"
          region = var.aws_region
          title  = "Disk and Swap Usage"
          yAxis = {
            left = {
              min = 0
              max = 100
            }
          }
        }
      }
    ]
  })
}

# CloudWatch Agent Installation (via user data)
resource "aws_ssm_document" "install_cloudwatch_agent" {
  name          = "${var.project_name}-install-cloudwatch-agent"
  document_type = "Command"
  
  content = jsonencode({
    schemaVersion = "2.2"
    description   = "Install and configure CloudWatch Agent"
    mainSteps = [
      {
        action = "aws:runShellScript"
        name   = "installCloudWatchAgent"
        inputs = {
          runCommand = [
            "#!/bin/bash",
            "# Download and install CloudWatch Agent",
            "wget https://s3.${var.aws_region}.amazonaws.com/amazoncloudwatch-agent-${var.aws_region}/ubuntu/amd64/latest/amazon-cloudwatch-agent.deb",
            "sudo dpkg -i -E ./amazon-cloudwatch-agent.deb",
            "# Configure and start the agent",
            "sudo /opt/aws/amazon-cloudwatch-agent/bin/amazon-cloudwatch-agent-ctl \\",
            "  -a fetch-config \\",
            "  -m ec2 \\",
            "  -s \\",
            "  -c ssm:${aws_ssm_parameter.cloudwatch_agent_config.name}"
          ]
        }
      }
    ]
  })
  
  tags = merge(var.common_tags, {
    Name = "${var.project_name}-cw-agent-install"
  })
}

# Outputs
output "sns_topic_arn" {
  description = "ARN of the SNS topic for alerts"
  value       = aws_sns_topic.crucible_alerts.arn
}

output "cloudwatch_dashboard_url" {
  description = "URL to the CloudWatch dashboard"
  value       = "https://${var.aws_region}.console.aws.amazon.com/cloudwatch/home?region=${var.aws_region}#dashboards:name=${aws_cloudwatch_dashboard.crucible_monitoring.dashboard_name}"
}

output "alert_email_configured" {
  description = "Email address configured for CloudWatch alerts"
  value       = local.alert_email != "" ? local.alert_email : "No alerts configured"
}