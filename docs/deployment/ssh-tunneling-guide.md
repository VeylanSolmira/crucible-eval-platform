# SSH Tunneling Guide for Crucible Platform

## What is SSH Tunneling?

SSH tunneling (also called SSH port forwarding) creates a secure connection between your local computer and a remote server. It's like creating a private tunnel through the internet.

```
Your Computer                    Internet                    EC2 Server
[localhost:8080] <---SSH Tunnel---> [22] <--Local Only--> [localhost:8080]
     |                                                           |
     v                                                           v
Web Browser                                              Crucible Platform
```

## Why Use SSH Tunneling?

1. **Security**: Platform never exposed to internet
2. **Privacy**: All traffic encrypted through SSH
3. **Simplicity**: No need for HTTPS certificates
4. **Access Control**: Only SSH key holders can connect

## Basic SSH Tunnel Command

```bash
ssh -L 8080:localhost:8080 ubuntu@<your-ec2-ip>
```

Breaking this down:
- `ssh`: The SSH command
- `-L`: Create a Local port forward
- `8080`: Your local port (on your computer)
- `localhost:8080`: Remote destination (on EC2)
- `ubuntu@<your-ec2-ip>`: SSH connection details

## Step-by-Step Setup

### 1. Get Your EC2 IP Address

```bash
# If using Terraform
cd infrastructure/terraform
tofu output eval_server_public_ip

# Or from AWS Console
aws ec2 describe-instances --query 'Reservations[*].Instances[*].PublicIpAddress'
```

### 2. Create the SSH Tunnel

```bash
# Basic tunnel
ssh -L 8080:localhost:8080 ubuntu@52.13.45.123

# With specific key file
ssh -i ~/.ssh/crucible-key.pem -L 8080:localhost:8080 ubuntu@52.13.45.123

# Keep connection alive (recommended)
ssh -o ServerAliveInterval=60 -L 8080:localhost:8080 ubuntu@52.13.45.123
```

### 3. Access the Platform

Once connected, open your browser to:
```
http://localhost:8080
```

This connects to your LOCAL port 8080, which tunnels to the EC2 server's port 8080.

## Advanced SSH Tunneling

### Multiple Port Forwarding

```bash
# Forward multiple ports in one connection
ssh -L 8080:localhost:8080 \
    -L 9090:localhost:9090 \
    -L 3000:localhost:3000 \
    ubuntu@<ec2-ip>
```

### Background Tunnel (No Shell)

```bash
# Create tunnel without opening a shell
ssh -N -f -L 8080:localhost:8080 ubuntu@<ec2-ip>

# -N: No remote command execution (just port forwarding)
# -f: Run in background (daemonize)

# To stop a background tunnel:
ps aux | grep "ssh -N" | grep 8080
kill <PID>
```

### Add Port Forwarding to Existing SSH Session

If you're already SSH'd in and forgot to add port forwarding:

```bash
# While in an SSH session:
# 1. Press Enter (to ensure you're on a new line)
# 2. Type: ~ (tilde - usually Shift+backtick)
# 3. Type: C (capital C - Shift+c)
# 4. You should see: ssh>

# If it doesn't work:
# - Make sure you press Enter first
# - Type ~ and C quickly (within 1 second)
# - The ~ must be the first character after Enter
# - Won't work if you're in a nested SSH session
# - May show "commandline disabled" if server disables this feature
#
# Why it might be disabled:
# - Server has PermitLocalCommand=no in /etc/ssh/sshd_config
# - Client has EscapeChar none in ~/.ssh/config
# - SSH was started with -e none option
# - Security policy blocks interactive commands

# Once you see ssh> prompt, type:
-L 8080:localhost:8080
# Press Enter

# The port is now forwarded without disconnecting!

# Other useful SSH escape sequences:
# ~.  - Disconnect
# ~?  - Show all escape sequences
# ~~  - Send a literal ~
```

### VS Code Port Forwarding

VS Code makes this even easier:

1. **Install Remote-SSH Extension**
   - Open VS Code
   - Install "Remote - SSH" extension

2. **Connect to EC2**
   - Cmd+Shift+P → "Remote-SSH: Connect to Host"
   - Enter: `ubuntu@<ec2-ip>`

3. **Forward Ports**
   - VS Code auto-detects running services
   - Or manually: Cmd+Shift+P → "Forward a Port"
   - Enter port: 8080
   - Access at http://localhost:8080

4. **View Forwarded Ports**
   - Open "Ports" panel (View → Terminal → Ports)
   - See all forwarded ports and their status

### Auto-Reconnecting Tunnel

```bash
# Using autossh (install with: brew install autossh)
autossh -M 0 -f -N \
    -o "ServerAliveInterval 30" \
    -o "ServerAliveCountMax 3" \
    -L 8080:localhost:8080 \
    ubuntu@<ec2-ip>

# -M 0: Disable monitoring port
# Automatically reconnects if connection drops
```

## Troubleshooting

### Connection Refused

```bash
# Check if service is running on EC2
ssh ubuntu@<ec2-ip> "sudo systemctl status crucible-platform"

# Check if port is listening
ssh ubuntu@<ec2-ip> "sudo netstat -tlnp | grep 8080"
```

### Address Already in Use

```bash
# Find what's using port 8080 locally
lsof -i :8080

# Kill the process (replace PID)
kill -9 <PID>

# Or use a different local port
ssh -L 8081:localhost:8080 ubuntu@<ec2-ip>
# Then browse to http://localhost:8081
```

### SSH Key Issues

```bash
# Fix key permissions
chmod 600 ~/.ssh/crucible-key.pem

# Specify key explicitly
ssh -i ~/.ssh/crucible-key.pem -L 8080:localhost:8080 ubuntu@<ec2-ip>
```

## SSH Config File (Recommended)

Create `~/.ssh/config`:

```
Host crucible
    HostName <your-ec2-ip>
    User ubuntu
    IdentityFile ~/.ssh/crucible-key.pem
    LocalForward 8080 localhost:8080
    LocalForward 9090 localhost:9090
    ServerAliveInterval 60
```

Then simply:
```bash
ssh crucible
```

## Security Best Practices

### 1. Restrict SSH Access

In your EC2 security group, only allow SSH from your IP:
```hcl
ingress {
  from_port   = 22
  to_port     = 22
  protocol    = "tcp"
  cidr_blocks = ["YOUR.IP.HERE/32"]  # Only your IP
}
```

### 2. Use SSH Keys (Never Passwords)

```bash
# Generate a strong key
ssh-keygen -t ed25519 -f ~/.ssh/crucible-key -C "crucible-platform"

# Add to EC2 (in Terraform)
variable "ssh_public_key" {
  default = "ssh-ed25519 AAAA... crucible-platform"
}
```

### 3. Monitor SSH Access

```bash
# Check SSH login attempts on EC2
ssh ubuntu@<ec2-ip> "sudo journalctl -u sshd -n 50"

# See active connections
ssh ubuntu@<ec2-ip> "who"
```

## Visual SSH Tunnel Diagram

```
┌─────────────────┐         ┌─────────────────────┐         ┌──────────────────┐
│  Your Computer  │         │    Internet         │         │   EC2 Instance   │
│                 │         │                     │         │                  │
│  Browser:8080 ──┼─────────┼─> SSH Tunnel:22 ───┼─────────┼─> Crucible:8080  │
│                 │         │   (Encrypted)       │         │   (Not Exposed)  │
└─────────────────┘         └─────────────────────┘         └──────────────────┘
```

## Why This Matters for METR

1. **Security First**: Evaluation platform never exposed to internet
2. **Audit Trail**: All access through SSH is logged
3. **Access Control**: Only authorized users with keys
4. **Development Friendly**: Easy local testing
5. **Production Ready**: Same pattern works at scale

## Quick Reference Card

```bash
# Basic tunnel
ssh -L 8080:localhost:8080 ubuntu@<ip>

# With keep-alive
ssh -o ServerAliveInterval=60 -L 8080:localhost:8080 ubuntu@<ip>

# Background tunnel
ssh -N -f -L 8080:localhost:8080 ubuntu@<ip>

# Kill background tunnel
ps aux | grep "ssh -N" | grep 8080
kill <PID>

# Check tunnel is working
curl http://localhost:8080/health
```

## Next Steps

1. **Test Your Tunnel**: Deploy and verify access
2. **Automate**: Add tunnel command to deployment output
3. **Document**: Add your EC2 IP to team docs
4. **Monitor**: Set up alerts for SSH access
5. **Scale**: Consider bastion host for team access