# Systemd Service Setup for Evaluation Platform

This directory contains systemd configuration for auto-starting the Crucible Evaluation Platform on boot.

## Files

- `evaluation-platform.service` - The systemd service definition
- `setup-systemd.sh` - Installation script
- `README.md` - This documentation

## Installation on EC2

1. Copy these files to your EC2 instance:
```bash
# From your local machine
scp -r infrastructure/systemd ubuntu@44.246.137.198:~/
```

2. SSH into the EC2 instance and run setup:
```bash
ssh ubuntu@44.246.137.198
cd ~/systemd
sudo ./setup-systemd.sh
```

## Service Configuration

The service is configured to:
- Start automatically on boot
- Restart on failure (with 10 second delay)
- Run as the `ubuntu` user (not root)
- Use memory and CPU limits to prevent resource exhaustion
- Log to systemd journal

## Customization

### Different Python Script
Edit the `ExecStart` line in the service file:
```ini
ExecStart=/usr/bin/python3 /home/ubuntu/evolution/extreme_mvp_monitoring_v3.py
```

### Environment Variables
Add environment variables in the `[Service]` section:
```ini
Environment="CRUCIBLE_PORT=8000"
Environment="CRUCIBLE_ENGINE=gvisor"
```

### Resource Limits
Adjust based on your instance size:
```ini
MemoryLimit=4G      # For larger instances
CPUQuota=100%       # Allow full CPU usage
```

## Monitoring

### View logs in real-time:
```bash
sudo journalctl -u evaluation-platform -f
```

### Check last 100 lines:
```bash
sudo journalctl -u evaluation-platform -n 100
```

### View logs from last boot:
```bash
sudo journalctl -u evaluation-platform -b
```

### Check service status:
```bash
sudo systemctl status evaluation-platform
```

## Troubleshooting

### Service won't start
1. Check logs: `sudo journalctl -u evaluation-platform -n 50`
2. Verify Python path: `which python3`
3. Check file permissions: `ls -la /home/ubuntu/evolution/`
4. Test manually: `python3 /home/ubuntu/evolution/extreme_mvp_frontier_events.py`

### Port already in use
```bash
# Find what's using port 8000
sudo lsof -i :8000

# Kill the process
sudo kill -9 <PID>
```

### Permission denied errors
Ensure the ubuntu user owns the evolution directory:
```bash
sudo chown -R ubuntu:ubuntu /home/ubuntu/evolution
```

## Security Notes

The service runs with:
- `NoNewPrivileges=true` - Prevents privilege escalation
- `PrivateTmp=true` - Isolated /tmp directory
- Non-root user - Runs as `ubuntu`, not root
- Resource limits - Prevents resource exhaustion

## Integration with CloudWatch (Optional)

To send logs to CloudWatch:

1. Install CloudWatch agent
2. Add to `/opt/aws/amazon-cloudwatch-agent/etc/config.json`:
```json
{
  "logs": {
    "logs_collected": {
      "journal": {
        "collect_list": [
          {
            "unit": "evaluation-platform"
          }
        ]
      }
    }
  }
}
```