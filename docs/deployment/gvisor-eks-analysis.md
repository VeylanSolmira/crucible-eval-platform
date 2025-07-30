# gVisor on EKS: Installation Analysis and Findings

## Executive Summary

After extensive testing, we discovered that installing gVisor on EKS nodes requires careful consideration of the EKS bootstrap process. While we successfully created a custom AMI with gVisor pre-installed, the containerd configuration does not persist through the EKS bootstrap process.

## Approaches Tested

### 1. User Data with MIME Format (Failed)
**What we tried:**
- Installing gVisor via user data in MIME multipart format
- Using containerd config drop-ins at `/etc/containerd/config.d/`

**Why it failed:**
- EKS requires specific MIME format, documentation is sparse
- Timing issues with EKS bootstrap script
- EKS containerd doesn't support config.d drop-ins
- Nodes failed to join cluster due to bootstrap interference

### 2. Custom AMI Approach (Partially Successful)
**What we tried:**
- Built custom AMI from EKS-optimized base (ami-000f73c884e4ca51a)
- Pre-installed gVisor binaries at `/usr/local/bin/runsc`
- Modified `/etc/containerd/config.toml` directly
- Added systemd dependencies

**Results:**
- ✅ AMI created successfully (ami-0be42842399d00fcc)
- ✅ gVisor binaries installed and verified
- ✅ Nodes join cluster successfully with bootstrap user data
- ❌ containerd doesn't recognize runsc runtime
- ❌ Pods fail with "no runtime for runsc is configured"

**Root cause:**
EKS bootstrap process overwrites `/etc/containerd/config.toml`, removing our gVisor configuration.

## Key Learnings

### 1. EKS Bootstrap Behavior
- EKS requires minimal user data even with custom AMIs: `/etc/eks/bootstrap.sh <cluster-name>`
- The bootstrap script modifies containerd configuration
- Drop-in configs at `/etc/containerd/config.d/` are not supported

### 2. Timing is Critical
- Modifications before bootstrap are overwritten
- Modifications during bootstrap interfere with node join
- Post-bootstrap modifications are required

### 3. Custom AMI Benefits
- Faster node startup (no download/install during boot)
- Consistent environment
- Reduced failure points during node creation

## Recommended Solutions

### Option 1: Custom AMI with Systemd Service (Best Long-term)
Build on our existing custom AMI (ami-0be42842399d00fcc) by adding a systemd service that configures containerd after EKS bootstrap completes.

**Systemd service (`/etc/systemd/system/configure-gvisor.service`):**
```bash
[Unit]
Description=Configure gVisor after EKS bootstrap
After=kubelet.service cloud-final.service
Requires=kubelet.service
Before=multi-user.target

[Service]
Type=oneshot
ExecStart=/usr/local/bin/configure-gvisor.sh
RemainAfterExit=yes
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

**Configuration script (`/usr/local/bin/configure-gvisor.sh`):**
```bash
#!/bin/bash
set -euo pipefail

LOG_FILE="/var/log/gvisor-config.log"
exec 1> >(tee -a "$LOG_FILE")
exec 2>&1

echo "[$(date)] Starting gVisor configuration..."

# Wait for kubelet to be fully running
while ! systemctl is-active --quiet kubelet; do
    echo "[$(date)] Waiting for kubelet..."
    sleep 5
done

# Wait for containerd to stabilize
sleep 10

# Backup current config
cp /etc/containerd/config.toml /etc/containerd/config.toml.backup

# Add gVisor runtime to containerd config
if ! grep -q "runsc" /etc/containerd/config.toml; then
    echo "[$(date)] Adding gVisor runtime to containerd config..."
    
    # Insert gVisor runtime configuration
    sed -i '/\[plugins."io.containerd.grpc.v1.cri".containerd.runtimes\]/a\
        [plugins."io.containerd.grpc.v1.cri".containerd.runtimes.runsc]\
          runtime_type = "io.containerd.runsc.v1"' /etc/containerd/config.toml
    
    # Restart containerd
    echo "[$(date)] Restarting containerd..."
    systemctl restart containerd
    
    # Wait for containerd to be ready
    sleep 5
    
    # Verify runtime is available
    if ctr plugin ls | grep -q runsc; then
        echo "[$(date)] SUCCESS: gVisor runtime configured"
    else
        echo "[$(date)] ERROR: gVisor runtime not found after configuration"
        exit 1
    fi
else
    echo "[$(date)] gVisor runtime already configured"
fi

echo "[$(date)] gVisor configuration complete"
```

**AMI build process updates:**
1. Install gVisor binaries (already done)
2. Create the systemd service file
3. Create the configuration script
4. Enable the service: `systemctl enable configure-gvisor.service`
5. Include minimal user data for EKS bootstrap

**Advantages over previous attempts:**
- Runs AFTER EKS has finished its configuration
- Doesn't interfere with node joining the cluster
- Idempotent - safe to run multiple times
- Logs available for debugging
- Clean rollback via backup

### Option 2: Init-Style DaemonSet (Quick Implementation)
Deploy a DaemonSet with init containers that:
1. Installs gVisor binaries (if not present)
2. Modifies containerd configuration
3. Restarts containerd service
4. Exits upon successful installation

**Implementation approach:**
```yaml
apiVersion: apps/v1
kind: DaemonSet
metadata:
  name: gvisor-installer
spec:
  template:
    spec:
      hostPID: true
      hostNetwork: true
      initContainers:
      - name: install-gvisor
        securityContext:
          privileged: true
        volumeMounts:
        - name: host-root
          mountPath: /host
        command: ["/install-gvisor.sh"]
      containers:
      - name: pause
        image: gcr.io/google_containers/pause:3.2
        resources:
          requests:
            cpu: "10m"
            memory: "10Mi"
```

**Pros:**
- Works with standard EKS AMIs
- Easy to update/rollback
- No custom AMI maintenance
- Init container exits after installation (minimal resource usage)
- Can be removed after all nodes are configured

**Cons:**
- Requires privileged access
- Temporary disruption during installation
- Less secure than pre-baked AMI

### Option 3: EKS-Managed Node Groups with Launch Templates
Use launch templates with proper MIME format and two-stage user data:
1. Stage 1: Pre-bootstrap binary installation
2. Stage 2: Post-bootstrap configuration via backgrounded script

## Security Considerations

1. **Pre-installed binaries** reduce attack surface vs. downloading at runtime
2. **Systemd service** approach maintains node integrity
3. **DaemonSet** requires careful RBAC and pod security policies
4. **Runtime verification** should be implemented regardless of approach

## Effort Estimates

1. **Custom AMI with systemd**: 2-3 days to implement and test
2. **DaemonSet approach**: 4-6 hours to implement
3. **Launch template refinement**: 1-2 days of testing

## Next Steps for Each Approach

### For Custom AMI with Systemd:
1. Create new EC2 instance from our existing AMI (ami-0be42842399d00fcc)
2. Add the systemd service and configuration script
3. Test the service works correctly after reboot
4. Create new AMI from the instance
5. Test with EKS node group deployment
6. Verify gVisor runtime is available after node joins cluster

### For Init-Style DaemonSet:
1. Create container image with gVisor installer script
2. Write DaemonSet manifest with proper security contexts
3. Deploy to single node first (using nodeSelector)
4. Validate gVisor installation and containerd restart
5. Roll out to all nodes
6. Monitor for any pod disruptions during containerd restart

### For Both Approaches:
- Implement health checks to verify gVisor availability
- Add monitoring/alerting for runtime status
- Create runbook for troubleshooting
- Document rollback procedures

## Recommendation

1. **Immediate (Today)**: Implement init-style DaemonSet for quick win
   - Can be deployed without infrastructure changes
   - Provides working gVisor while we refine AMI approach
   
2. **This Week**: Refine custom AMI with systemd service
   - More reliable and secure long-term solution
   - Better performance (no installation on boot)
   - Easier to audit and compliance-friendly

3. **Future**: Consider Bottlerocket OS
   - Purpose-built for containers with better runtime support
   - Immutable OS with atomic updates
   - Native support for multiple container runtimes

## Development AMI for Systemd Testing

To enable rapid iteration on the systemd approach, we can create a development AMI with SSH/SSM access:

### Create Development AMI from Our Custom AMI

```bash
# Start an instance from our custom AMI (ami-0be42842399d00fcc)
aws ec2 run-instances \
  --image-id ami-0be42842399d00fcc \
  --instance-type t3.small \
  --subnet-id <subnet-id> \
  --security-group-ids <sg-id> \
  --iam-instance-profile Name=<instance-profile> \
  --user-data file://enable-access.sh \
  --tag-specifications 'ResourceType=instance,Tags=[{Key=Name,Value=gvisor-dev-ami-builder}]'
```

### User Data to Enable Access

```bash
#!/bin/bash
# enable-access.sh

# Enable SSM agent (already installed on EKS AMIs)
systemctl enable amazon-ssm-agent
systemctl start amazon-ssm-agent

# Optional: Enable SSH (for development only)
# echo "ssh-rsa YOUR_PUBLIC_KEY" >> /home/ec2-user/.ssh/authorized_keys
```

### Install Systemd Service Files

Once connected via SSM:

```bash
# Create the systemd service
cat > /etc/systemd/system/configure-gvisor.service << 'EOF'
[Unit]
Description=Configure gVisor after EKS bootstrap
After=kubelet.service cloud-final.service
Requires=kubelet.service
Before=multi-user.target

[Service]
Type=oneshot
ExecStart=/usr/local/bin/configure-gvisor.sh
RemainAfterExit=yes
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

# Create the configuration script
cat > /usr/local/bin/configure-gvisor.sh << 'EOF'
#!/bin/bash
set -euo pipefail

LOG_FILE="/var/log/gvisor-config.log"
exec 1> >(tee -a "$LOG_FILE")
exec 2>&1

echo "[$(date)] Starting gVisor configuration..."

# Wait for kubelet to be fully running
while ! systemctl is-active --quiet kubelet; do
    echo "[$(date)] Waiting for kubelet..."
    sleep 5
done

# Extra wait for containerd to stabilize
sleep 10

# Backup current config
cp /etc/containerd/config.toml /etc/containerd/config.toml.backup-$(date +%s)

# Add gVisor runtime to containerd config if not present
if ! grep -q "runsc" /etc/containerd/config.toml; then
    echo "[$(date)] Adding gVisor runtime to containerd config..."
    
    # Insert gVisor runtime configuration
    sed -i '/\[plugins."io.containerd.grpc.v1.cri".containerd.runtimes\]/a\
        [plugins."io.containerd.grpc.v1.cri".containerd.runtimes.runsc]\
          runtime_type = "io.containerd.runsc.v1"' /etc/containerd/config.toml
    
    # Restart containerd
    echo "[$(date)] Restarting containerd..."
    systemctl restart containerd
    
    # Wait for containerd
    sleep 5
    
    # Verify runtime is available
    if ctr plugin ls | grep -q runsc; then
        echo "[$(date)] SUCCESS: gVisor runtime configured"
    else
        echo "[$(date)] ERROR: gVisor runtime not found after configuration"
        exit 1
    fi
else
    echo "[$(date)] gVisor runtime already configured"
fi

echo "[$(date)] gVisor configuration complete"
EOF

chmod +x /usr/local/bin/configure-gvisor.sh

# Enable the service
systemctl enable configure-gvisor.service

# Test it
systemctl start configure-gvisor.service
systemctl status configure-gvisor.service
```

### Create Production AMI

After testing and refinement:

```bash
# Create AMI without SSH/SSM access for production
aws ec2 create-image \
  --instance-id <instance-id> \
  --name "eks-optimized-gvisor-systemd-v2" \
  --description "EKS AMI with gVisor and systemd service"
```

### Key Testing Points

1. **Service timing**: Ensure service runs after EKS bootstrap
2. **Containerd restart**: Verify it doesn't disrupt kubelet
3. **Idempotency**: Service should handle repeated runs
4. **Reboot testing**: Verify gVisor remains configured after reboot