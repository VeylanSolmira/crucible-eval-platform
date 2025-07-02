# Docker Networking: Deep Internals

## How Docker Networking Actually Works

### Network Namespaces
```bash
# Each container gets its own network namespace
docker run --rm alpine ip addr
# Shows only container's interfaces

# Host network namespace
ip addr
# Shows all host interfaces
```

Docker uses Linux network namespaces to isolate containers:
- Each container has its own network stack
- Own routing table, iptables rules, network devices
- Connected via virtual ethernet pairs (veth)

### Bridge Networks (Default)
```
Host eth0 ← docker0 bridge ← veth pairs → Containers
         172.17.0.1      172.17.0.2, 172.17.0.3...
```

```bash
# See the bridge
brctl show docker0
ip addr show docker0

# See iptables rules Docker creates
iptables -t nat -L DOCKER
```

### Container-to-Container Communication
```
Container A → veth → docker0 bridge → veth → Container B
         ARP for B's IP → Bridge forwards → B receives
```

1. Container A wants to reach service "queue"
2. Docker's embedded DNS resolves "queue" → 172.17.0.3
3. Packet goes through veth to docker0
4. Bridge forwards to Container B's veth
5. Container B receives packet

### Custom Networks
```yaml
networks:
  backend:
    driver: bridge
    ipam:
      config:
        - subnet: 10.5.0.0/16
```

Creates a new bridge (br-xxxx) with:
- Its own subnet
- Isolated from default bridge
- Embedded DNS for service discovery
- Automatic container DNS entries

## Performance Deep Dive

### Network Modes Performance
```
1. Host mode (--network host): Native performance
   - No NAT, no bridge
   - Container uses host interfaces directly
   - Security implications!

2. Bridge mode: ~5% overhead
   - NAT translation
   - Bridge forwarding
   - Good isolation

3. Overlay networks: ~10-15% overhead  
   - VXLAN encapsulation
   - For multi-host networking
   - Kubernetes/Swarm use this

4. Macvlan: ~2% overhead
   - Container gets real MAC address
   - Appears as physical host on network
```

### TCP vs UDP in Containers
```python
# TCP: Connection state tracked by Docker
# UDP: Stateless, faster but less reliable

# For queue service, TCP is right choice
# For metrics/logging, UDP might be better
```

### iptables Rules (What Docker Does)
```bash
# PREROUTING: Incoming packets
-A PREROUTING -m addrtype --dst-type LOCAL -j DOCKER

# OUTPUT: Locally generated packets  
-A OUTPUT ! -d 127.0.0.0/8 -m addrtype --dst-type LOCAL -j DOCKER

# POSTROUTING: Source NAT for outgoing
-A POSTROUTING -s 172.17.0.0/16 ! -o docker0 -j MASQUERADE

# DOCKER chain: Port forwarding
-A DOCKER -p tcp -m tcp --dport 8080 -j DNAT --to 172.17.0.2:8080
```

## Security Internals

### Network Isolation Mechanisms

1. **Namespace Isolation**
```c
// Kernel level isolation
clone(CLONE_NEWNET)  // New network namespace
```

2. **Seccomp Filters**
```json
{
  "syscalls": [
    {
      "names": ["socket"],
      "action": "SCMP_ACT_ERRNO",
      "args": [
        {
          "index": 0,
          "value": 16,  // AF_PACKET (raw sockets)
          "op": "SCMP_CMP_EQ"
        }
      ]
    }
  ]
}
```

3. **AppArmor/SELinux**
```
# Prevent network access
deny network,

# Allow only specific ports
allow network tcp dst 8080,
```

### DNS in Docker

Docker runs an embedded DNS server at 127.0.0.11:
```bash
# Inside container
cat /etc/resolv.conf
# nameserver 127.0.0.11

# How it works:
Container → 127.0.0.11:53 → Docker daemon → Response
                         ↓
                  Checks service names
                  Falls back to host DNS
```

## Advanced Patterns

### 1. Service Mesh Sidecar
```yaml
# Each container gets a proxy sidecar
services:
  api:
    image: api:latest
  
  api-proxy:  # Envoy/Linkerd sidecar
    image: envoyproxy/envoy
    network_mode: "service:api"  # Share network namespace
```

### 2. Network Policies (CNI)
```yaml
# Calico/Cilium provide kernel-level filtering
apiVersion: "projectcalico.org/v3"
kind: NetworkPolicy
spec:
  selector: app == 'queue'
  ingress:
  - action: Allow
    source:
      selector: app == 'api'
  egress:
  - action: Deny  # Deny all egress
```

### 3. eBPF for Observability
```c
// Modern kernel tracing
SEC("kprobe/tcp_connect")
int trace_connect(struct pt_regs *ctx) {
    // Log all TCP connections
}
```

## Debugging Tools

### 1. Network Namespace Debugging
```bash
# Enter container namespace
docker exec -it container_name bash
nsenter -t $(docker inspect -f '{{.State.Pid}}' container) -n bash

# See all network activity
tcpdump -i any -n
```

### 2. Connection Tracking
```bash
# See NAT translations
conntrack -L

# See specific container
docker exec container_name ss -tan
```

### 3. Performance Analysis
```bash
# Latency testing
docker exec container_a ping container_b

# Bandwidth testing  
docker exec container_a iperf3 -c container_b

# TCP dump for packet analysis
tcpdump -i docker0 -w capture.pcap
```

## Multi-Host Networking

### Overlay Networks (VXLAN)
```
Host A                          Host B
Container → docker_gwbridge → VXLAN tunnel → docker_gwbridge → Container
         ↓                                  ↑
      eth0 ←────── Physical Network ────→ eth0
```

### Encryption
```bash
# Create encrypted overlay
docker network create --opt encrypted --driver overlay secure-net
```
Uses IPsec for transport encryption (20-30% overhead)

## Performance Tuning

### 1. Kernel Parameters
```bash
# /etc/sysctl.conf
net.core.somaxconn = 65535
net.ipv4.tcp_max_syn_backlog = 65535
net.core.netdev_max_backlog = 65535
```

### 2. Container Limits
```yaml
services:
  api:
    sysctls:
      - net.core.somaxconn=1024
    ulimits:
      nofile:
        soft: 65535
        hard: 65535
```

### 3. Network Driver Options
```yaml
networks:
  perf_net:
    driver_opts:
      com.docker.network.driver.mtu: 9000  # Jumbo frames
```

## Common Issues & Solutions

### 1. "Cannot connect to container"
- Check network membership: `docker inspect container_name | grep NetworkMode`
- Verify DNS: `docker exec container_name nslookup service_name`
- Check iptables: `iptables -L DOCKER`

### 2. "Slow network performance"
- Check for packet loss: `ping -c 100 service_name`
- Verify MTU: `ip link show docker0`
- Look for retransmissions: `netstat -s | grep -i retrans`

### 3. "Random connection failures"
- Conntrack table full: `sysctl net.netfilter.nf_conntrack_count`
- Increase limit: `sysctl -w net.netfilter.nf_conntrack_max=262144`

## Platform Lead Takeaways

1. **Default is usually fine** - Bridge networking works for 90% of cases
2. **Isolate by function** - Separate networks for different concerns
3. **Monitor conntrack** - Common production issue
4. **DNS is critical** - Many issues trace back to DNS
5. **Test under load** - Network issues often appear at scale

## Further Reading

- [Linux Network Namespaces](https://man7.org/linux/man-pages/man7/network_namespaces.7.html)
- [Docker libnetwork Design](https://github.com/moby/libnetwork/blob/master/docs/design.md)
- [CNI Specification](https://github.com/containernetworking/cni/blob/master/SPEC.md)
- [eBPF for Networking](https://cilium.io/blog/2018/04/17/why-is-the-kernel-community-replacing-iptables/)