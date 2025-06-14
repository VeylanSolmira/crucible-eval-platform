# Port 80 Mapping Guide: Direct Browser Access

## Why Map to Port 80?

Port 80 is the default HTTP port, allowing access via `http://server-ip` without specifying a port. However, this comes with security trade-offs.

## Methods to Map Port 8080 → Port 80

### Option 1: Run Application on Port 80 (NOT Recommended)

```bash
# Requires root because ports < 1024 are privileged
sudo /home/ubuntu/crucible/venv/bin/python /home/ubuntu/crucible/app.py --port 80
```

**Problems:**
- Application runs as root (massive security risk)
- If app is compromised, attacker has root access
- Violates principle of least privilege
- Would need to modify systemd service to run as root

### Option 2: iptables Port Forwarding

Redirect incoming port 80 traffic to port 8080:

```bash
# Add redirect rules
sudo iptables -t nat -A PREROUTING -p tcp --dport 80 -j REDIRECT --to-port 8080
sudo iptables -t nat -A OUTPUT -p tcp --dport 80 -j REDIRECT --to-port 8080

# Make persistent across reboots
sudo apt-get install iptables-persistent
sudo netfilter-persistent save
```

**Pros:**
- App continues running as non-root user
- Simple to implement
- No additional services needed

**Cons:**
- Can be confusing to debug
- Rules can be accidentally cleared
- Need to manage iptables rules

### Option 3: Nginx Reverse Proxy (RECOMMENDED)

Use nginx to proxy requests from port 80 to your app on 8080:

```bash
# Install nginx
sudo apt-get update
sudo apt-get install nginx

# Create configuration
sudo tee /etc/nginx/sites-available/crucible << 'EOF'
server {
    listen 80;
    server_name _;
    
    # Proxy to application
    location / {
        proxy_pass http://localhost:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # WebSocket support (if needed)
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
    
    # Health check endpoint
    location /nginx-health {
        access_log off;
        return 200 "healthy\n";
        add_header Content-Type text/plain;
    }
}
EOF

# Enable the site
sudo ln -s /etc/nginx/sites-available/crucible /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default

# Test configuration
sudo nginx -t

# Restart nginx
sudo systemctl restart nginx
sudo systemctl enable nginx
```

**Pros:**
- Industry standard approach
- Nginx handles static files efficiently
- Can add HTTPS termination later
- Built-in load balancing capabilities
- Request logging and metrics

**Cons:**
- Additional service to manage
- Extra layer of complexity
- Small performance overhead

### Option 4: systemd Socket Activation

Let systemd listen on port 80 and pass connections to your app:

```ini
# /etc/systemd/system/crucible-platform.socket
[Unit]
Description=Crucible Platform Socket

[Socket]
ListenStream=80

[Install]
WantedBy=sockets.target
```

**Note:** Requires application changes to support socket activation.

## Security Group Changes Required

For any of these options, you need to open port 80:

```hcl
# In Terraform
ingress {
  from_port   = 80
  to_port     = 80
  protocol    = "tcp"
  cidr_blocks = ["0.0.0.0/0"]  # Open to world - be careful!
}
```

## Why NOT Run Web Servers as Root in Production?

**Common misconception:** Production web servers DON'T run as root!

### How Production Actually Works:

1. **Nginx/Apache:**
   - Master process starts as root (to bind port 80)
   - Immediately spawns worker processes as `www-data` or `nginx` user
   - Workers handle all requests (never run as root)
   - Master only manages workers, doesn't serve traffic

2. **Node.js/Python in Production:**
   - Use reverse proxy (nginx) on port 80
   - App runs on high port (8080) as non-root
   - Or use capabilities: `sudo setcap 'cap_net_bind_service=+ep' /usr/bin/python3`

3. **Container/Kubernetes:**
   - Containers run as non-root users
   - Ingress controller handles port 80
   - Apps run on high ports internally

### The Security Model:

```
Internet → Port 80 → Nginx (root → www-data) → Port 8080 → App (non-root)
```

**Never** in production:
```
Internet → Port 80 → App running as root  ❌
```

### Why This Matters:

1. **Privilege Separation**: If nginx is compromised, attacker only gets `www-data` user
2. **Defense in Depth**: Multiple layers of security
3. **Principle of Least Privilege**: Each component has minimum required permissions
4. **Blast Radius**: Compromise is contained to unprivileged user

## Recommended Approach for Crucible

### Development:
- Use SSH tunneling (secure, simple, no open ports)
- Access via `localhost:8080`

### Production:
1. Nginx reverse proxy on port 80/443
2. Application on port 8080 as non-root
3. HTTPS with Let's Encrypt
4. CloudFlare or AWS ALB in front

### Why SSH Tunneling for Development:
- No open ports to internet
- Encrypted by default
- No need for HTTPS certificates
- Works behind firewalls
- Prevents accidental exposure

## Quick Decision Matrix

| Method | Security | Complexity | Use Case |
|--------|----------|------------|----------|
| App on port 80 as root | ❌ Terrible | Simple | Never |
| iptables redirect | ✅ Good | Medium | Quick solutions |
| Nginx reverse proxy | ✅ Best | Medium | Production standard |
| SSH tunnel | ✅ Best | Simple | Development/testing |

## The Golden Rule

> "If your application runs as root in production, you're doing it wrong."

Production web servers use privilege separation: root only for binding ports, then dropping to unprivileged users for actual work.

## Why SSH Tunneling Over Nginx for Development?

You might ask: "If nginx reverse proxy (Option 3) is secure and production-ready, why use SSH tunneling for development?"

### SSH Tunneling Advantages for Development:

1. **Zero Configuration**
   - SSH tunnel: One command, done
   - Nginx: Install, configure, test, restart, manage

2. **No Open Ports**
   - SSH tunnel: Only port 22 (SSH) open
   - Nginx: Must open port 80 to the world (0.0.0.0/0)

3. **No Public Exposure**
   - SSH tunnel: Impossible for random internet scanners to find
   - Nginx: Your dev server is now on Shodan/bot scanning lists

4. **Built-in Encryption**
   - SSH tunnel: All traffic encrypted via SSH
   - Nginx (port 80): Unencrypted HTTP traffic

5. **No DNS/Certificate Hassles**
   - SSH tunnel: Works with localhost
   - Nginx HTTPS: Need domain, certificates, renewal

6. **Easier Debugging**
   - SSH tunnel: One process, simple flow
   - Nginx: Debug both nginx AND your app

7. **Security Through Obscurity** (for dev)
   - SSH tunnel: Attacker needs your SSH key
   - Nginx: Anyone can hit http://your-ec2-ip

### When to Use Each:

**SSH Tunneling:**
- Development environments
- Testing deployments
- Debugging production issues
- Internal tools
- When you want zero internet exposure

**Nginx Reverse Proxy:**
- Production deployments
- When you need public access
- Multiple applications on one server
- Need load balancing
- Want caching, compression, etc.

### The Development Security Model:

```
Your Laptop → SSH (encrypted) → EC2 Port 22 → Local forward → App Port 8080
   Safe                            Only open port           Never exposed
```

vs.

```
Internet → EC2 Port 80 → Nginx → App Port 8080
Anyone    Must be open   Extra layer
```

### Real-World Example:

Even at big tech companies, developers use SSH tunneling for:
- Accessing internal dashboards
- Debugging production services
- Testing deployments
- Anything that doesn't need public access

The nginx reverse proxy is the right tool for production, but it's overkill for development where SSH tunneling is simpler, more secure, and requires zero configuration on the server.

### Bottom Line:

- **Development**: SSH tunneling = maximum security with minimum effort
- **Production**: Nginx reverse proxy = scalable public access with proper security

Using nginx for development is like wearing a tuxedo to debug code - it works, but it's unnecessarily formal!