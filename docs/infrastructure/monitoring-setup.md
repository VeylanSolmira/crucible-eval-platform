# CloudWatch Monitoring Setup

This Terraform configuration sets up comprehensive monitoring for the Crucible Platform, specifically designed to handle memory-constrained environments like t2.micro instances.

## Features

### Intelligent Alerts
- **OOM Kill Detection** - Immediate alerts when containers are killed due to memory
- **Container Restart Detection** - Alerts on crash loops (>5 restarts in 15 min)
- **Low Memory Alerts** - Triggers when available memory drops below 100MB (absolute, not percentage)
- **Memory Pressure Alerts** - Sustained high memory usage (>95% for 5 minutes)
- **Swap Usage Alerts** - Indicates memory pressure when swap usage exceeds 25%
- **Container Start Failures** - Alerts when containers fail to start
- **Docker Daemon Errors** - Catches Docker-level issues
- **Disk Usage Alerts** - Warns when disk usage exceeds 85%

### Metrics Collection
- Memory usage (used, available, percentage)
- CPU utilization
- Disk usage and I/O
- Network statistics
- Container-specific metrics
- Custom application metrics

### CloudWatch Dashboard
A pre-configured dashboard showing:
- Memory usage and availability
- Container issues (OOM kills, restarts, failures)
- CPU usage
- Disk and swap usage

## Setup Instructions

### 1. Enable Monitoring
```bash
# Set your alert email (optional)
export TF_VAR_alert_email="your-email@example.com"

# Apply the monitoring configuration
terraform apply
```

### 2. Access the Dashboard
After deployment, access your dashboard at:
```
https://us-west-2.console.aws.amazon.com/cloudwatch/home?region=us-west-2#dashboards:name=crucible-platform-monitoring
```

### 3. View Alerts
Check configured alarms at:
```
https://us-west-2.console.aws.amazon.com/cloudwatch/home?region=us-west-2#alarmsV2:alarmFilter=ANY
```

## Testing the Monitoring

### Simulate OOM Kill
```bash
# SSH to instance and run a memory-consuming container
docker run --rm -m 50m alpine sh -c "dd if=/dev/zero of=/dev/null bs=100M"
```

### Check Memory Usage
```bash
# Via AWS CLI
aws cloudwatch get-metric-statistics \
  --namespace "crucible-platform/System" \
  --metric-name mem_used_percent \
  --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 300 \
  --statistics Average
```

### View Container Logs
```bash
# View recent OOM events
aws logs filter-log-events \
  --log-group-name "/aws/ec2/crucible-platform/docker" \
  --filter-pattern "OOMKilled"
```

## Customization

### Adjust Thresholds
Edit `monitoring.tf` to change alert thresholds:
```hcl
# Example: Change low memory threshold to 50MB
threshold = "52428800"  # 50MB in bytes
```

### Add Custom Metrics
Add new log metric filters for specific patterns:
```hcl
resource "aws_cloudwatch_log_metric_filter" "custom_error" {
  name           = "${var.project_name}-custom-errors"
  log_group_name = aws_cloudwatch_log_group.crucible_docker.name
  pattern        = "[time, id, level, component, msg = \"*YOUR_ERROR_PATTERN*\"]"
  
  metric_transformation {
    name      = "CustomErrorCount"
    namespace = "${var.project_name}/Application"
    value     = "1"
  }
}
```

## Cost Considerations

Estimated monthly costs (us-west-2):
- CloudWatch Agent: Free (basic metrics)
- Custom Metrics: ~$0.30/metric/month (first 10K API requests free)
- Log Ingestion: ~$0.50/GB
- Log Storage: ~$0.03/GB/month
- Alarms: ~$0.10/alarm/month
- Dashboard: First 3 dashboards free

**Total estimate for t2.micro monitoring**: ~$5-10/month

## Troubleshooting

### CloudWatch Agent Not Starting
```bash
# Check agent status
sudo /opt/aws/amazon-cloudwatch-agent/bin/amazon-cloudwatch-agent-ctl \
  -a query -m ec2

# View agent logs
sudo tail -f /opt/aws/amazon-cloudwatch-agent/logs/amazon-cloudwatch-agent.log
```

### Missing Metrics
1. Verify IAM role has `CloudWatchAgentServerPolicy`
2. Check agent configuration in SSM Parameter Store
3. Ensure log groups exist with proper permissions

### No Alerts Firing
1. Check alarm state in CloudWatch console
2. Verify SNS topic subscription is confirmed
3. Test with manual metric data:
```bash
aws cloudwatch put-metric-data \
  --namespace "crucible-platform/Containers" \
  --metric-name "OOMKillCount" \
  --value 1
```

## Next Steps

1. **Set up anomaly detection** for unusual patterns
2. **Create runbooks** for each alert type
3. **Implement auto-remediation** for common issues
4. **Add application-specific metrics** from your services