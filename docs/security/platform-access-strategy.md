# Platform Access Strategy: From Development to Public Access

## Overview
This document outlines the security requirements needed to transition from IP whitelisting (current development phase) to public access, ensuring the platform can be safely opened to researchers once proper security measures are in place.

## The Fundamental Tension

### Security Risks of Public Access

1. **Resource Exhaustion Attacks**
   - Malicious actors submitting infinite loops, fork bombs, memory exhaustion code
   - Even with limits, coordinated attacks could overwhelm the system
   - Cost implications: Each execution consumes real compute resources

2. **Platform as Attack Vector**
   - Code execution platform could be used to:
     - Mine cryptocurrency
     - Launch attacks on other systems
     - Exfiltrate data from the execution environment
     - Test malware in an isolated environment

3. **AI Safety Research Risks**
   - Adversaries learning how AI systems are evaluated
   - Gaming the evaluation metrics
   - Discovering weaknesses in safety measures
   - Using the platform to develop more capable AI systems

4. **Intellectual Property Concerns**
   - Evaluation methodologies and benchmarks may be proprietary
   - Test cases could reveal safety research directions
   - Infrastructure design could be valuable IP

### Benefits of Researcher Access

1. **Advancing AI Safety**
   - More researchers can contribute to safety evaluations
   - Diverse perspectives improve robustness
   - Reproducible research requires accessible platforms

2. **Building Trust**
   - Transparency in evaluation methods
   - Independent verification of results
   - Community confidence in safety claims

3. **Ecosystem Development**
   - Standardized evaluation infrastructure
   - Shared benchmarks and methodologies
   - Collaborative safety research

## Current Implementation Analysis

The platform is taking a **phased approach**:

### Phase 1: Internal Development (Past)
- Local development only
- No network access controls
- Focus on core functionality

### Phase 2: Controlled Beta (Current)
```hcl
# Current Terraform configuration shows:
variable "allowed_web_ips" {
  description = "IPs allowed HTTPS/HTTP access"
  type        = list(string)
  default     = [] # Must be explicitly set
}

# Security group rules enforce IP restrictions:
ingress {
  from_port   = 443
  to_port     = 443
  protocol    = "tcp"
  cidr_blocks = var.allowed_web_ips
}
```

**Current Security Model:**
- IP whitelist for all access
- No user authentication
- Basic rate limiting (30 req/s general, 10 req/s API)
- Strong container isolation (gVisor)

### Phase 3: Trusted Researcher Access (Planned)
From the security documentation:
- CloudFlare Zero Trust integration
- Email-based authentication
- Researcher vetting process
- Usage monitoring and quotas

### Phase 4: Broader Access (If Needed)
- Full authentication system (OAuth2/JWT)
- Aggressive rate limiting
- WAF rules
- Cost recovery mechanisms

## Recommended Security Model

### 1. Tiered Access System

```yaml
Access Tiers:
  Public:
    - Read-only documentation
    - Example evaluations
    - Limited API access (heavily rate-limited)
    
  Registered Researchers:
    - Email verification required
    - Affiliation verification
    - Higher rate limits
    - Access to standard benchmarks
    
  Trusted Partners:
    - Manual vetting process
    - Full platform access
    - Custom evaluation capabilities
    - Access to sensitive benchmarks
    
  Internal:
    - Unrestricted access
    - Administrative capabilities
    - Infrastructure management
```

### 2. Progressive Security Controls

```python
# Pseudocode for access control
def check_access(request, resource):
    # Layer 1: Network level
    if not ip_in_allowlist(request.ip) and not has_cloudflare_auth(request):
        return deny("Network access denied")
    
    # Layer 2: Authentication
    user = authenticate(request)
    if not user and resource.requires_auth:
        return deny("Authentication required")
    
    # Layer 3: Authorization
    if not user.has_permission(resource):
        return deny("Insufficient permissions")
    
    # Layer 4: Rate limiting
    if exceeded_rate_limit(user, resource):
        return deny("Rate limit exceeded", retry_after=calculate_backoff())
    
    # Layer 5: Resource limits
    if not within_resource_quota(user):
        return deny("Resource quota exceeded")
    
    return allow()
```

### 3. Security Through Economic Constraints

```typescript
// Make attacks economically unviable
interface UsageQuotas {
  free_tier: {
    executions_per_day: 10,
    max_execution_time: 30, // seconds
    max_memory: 512, // MB
    max_cpu: 0.5, // cores
  },
  
  researcher_tier: {
    executions_per_day: 1000,
    max_execution_time: 300,
    max_memory: 4096,
    max_cpu: 2,
    cost_per_execution: 0.01, // USD
  },
  
  partner_tier: {
    executions_per_day: 10000,
    max_execution_time: 3600,
    max_memory: 16384,
    max_cpu: 8,
    negotiated_pricing: true,
  }
}
```

### 4. Monitoring and Anomaly Detection

```python
# Security monitoring patterns
class SecurityMonitor:
    def analyze_execution(self, code, metadata):
        checks = [
            self.check_crypto_mining_patterns(code),
            self.check_network_attempt_patterns(code),
            self.check_resource_exhaustion_patterns(code),
            self.check_known_exploit_patterns(code),
            self.check_anomalous_behavior(code, metadata),
        ]
        
        risk_score = sum(check.risk_level for check in checks)
        
        if risk_score > THRESHOLD:
            self.alert_security_team(code, metadata, checks)
            return ExecutionDenied("Suspicious pattern detected")
```

## Security Requirements Before Removing IP Whitelisting

### Minimum Viable Security (Must Have)

Before removing IP restrictions, these security measures MUST be in place:

#### 1. Authentication System
```typescript
// Required implementation
interface AuthSystem {
  // User registration with email verification
  register(email: string, password: string): Promise<User>;
  
  // Rate-limited login
  login(email: string, password: string): Promise<Session>;
  
  // JWT or session-based auth
  validateSession(token: string): Promise<User | null>;
  
  // Password reset flow
  resetPassword(email: string): Promise<void>;
}
```

#### 2. Authorization & Quotas
```typescript
interface UserQuotas {
  daily_executions: number;      // e.g., 100
  max_execution_time: number;    // e.g., 60 seconds
  max_memory_mb: number;         // e.g., 1024
  concurrent_executions: number; // e.g., 2
}

// Enforce at API level
async function checkQuota(userId: string): Promise<boolean> {
  const usage = await getUsageToday(userId);
  const quota = await getUserQuota(userId);
  return usage.executions < quota.daily_executions;
}
```

#### 3. Enhanced Rate Limiting
```nginx
# Current: 10 req/s for API
# Needed: Per-user rate limiting
limit_req_zone $jwt_sub zone=peruser:10m rate=5r/s;
limit_req_zone $jwt_sub zone=expensive:10m rate=1r/m;

# Apply to endpoints
location /api/eval {
    limit_req zone=peruser burst=10 nodelay;
    limit_req zone=expensive burst=2 nodelay;
}
```

#### 4. Abuse Detection
```python
# Patterns to detect and block
SUSPICIOUS_PATTERNS = [
    r'subprocess|os\.system|eval|exec|compile',  # Dangerous functions
    r'while\s+True|for\s+i\s+in\s+range\(10\*\*',  # Infinite loops
    r'fork\(\)|multiprocessing|threading',  # Resource exhaustion
    r'socket|urllib|requests|http',  # Network attempts
    r'nvidia|cuda|gpu',  # Crypto mining
]

def pre_execution_check(code: str) -> tuple[bool, str]:
    for pattern in SUSPICIOUS_PATTERNS:
        if re.search(pattern, code, re.IGNORECASE):
            return False, f"Suspicious pattern detected: {pattern}"
    return True, "OK"
```

#### 5. Cost Protection
```typescript
// Implement spending limits
interface CostProtection {
  // Track costs per user
  async trackExecution(userId: string, resources: ResourceUsage): Promise<void>;
  
  // Daily spending limit
  daily_cost_limit: number; // e.g., $10
  
  // Auto-suspend users exceeding limits
  async checkCostLimit(userId: string): Promise<boolean>;
}
```

### Nice to Have (Can Add Later)

These can be implemented after launch:

1. **2FA/MFA** - Additional account security
2. **API Keys** - For programmatic access
3. **Team Accounts** - Shared quotas
4. **Billing System** - For users needing higher quotas
5. **Advanced Analytics** - Usage patterns, anomaly detection

## Implementation Roadmap

### Near-term (Current Phase)
1. **Maintain IP whitelisting** for alpha/beta testing
2. **Implement basic telemetry** to understand usage patterns
3. **Document acceptable use policies**
4. **Create researcher application process**

### Medium-term (3-6 months)
1. **Implement tiered access system**
2. **Add CloudFlare Zero Trust as planned**
3. **Build usage monitoring dashboard**
4. **Establish cost recovery model**

### Long-term (6-12 months)
1. **Consider open-sourcing non-sensitive components**
2. **Build researcher community with strict vetting**
3. **Implement advanced anomaly detection**
4. **Establish bug bounty program**

## Alternative Models to Consider

### 1. Compute Donation Model
```yaml
# Researchers contribute compute in exchange for access
contribution_tiers:
  - donate_compute: 100_hours
    receive_access: 1000_executions
  - donate_compute: 1000_hours
    receive_access: unlimited_with_fair_use
```

### 2. Academic Partnership Model
- Partner with universities
- Access through institutional credentials
- Shared research outcomes
- Cost sharing agreements

### 3. Gradual Open Source
```
Phase 1: Open source the execution environment
Phase 2: Open source the basic evaluation framework  
Phase 3: Keep advanced benchmarks and safety tests private
Phase 4: Provide hosted service for convenience
```

## Security Checklist for Public Launch

- [ ] Implement comprehensive authentication system
- [ ] Deploy WAF with custom rules
- [ ] Set up DDoS protection (CloudFlare)
- [ ] Implement cost controls and billing
- [ ] Create abuse detection system
- [ ] Establish incident response procedures
- [ ] Legal framework (ToS, Privacy Policy, Acceptable Use)
- [ ] Security audit by third party
- [ ] Penetration testing
- [ ] Load testing at 10x expected capacity
- [ ] Backup and recovery procedures
- [ ] Data retention policies
- [ ] GDPR/privacy compliance

## Quick Start: What to Build First

To remove IP whitelisting and open the platform, implement in this order:

1. **Basic Auth** (1-2 weeks)
   - User registration/login
   - JWT tokens
   - Session management

2. **User Quotas** (3-5 days)
   - Database schema for tracking usage
   - Middleware to enforce limits
   - Basic dashboard

3. **Abuse Detection** (1 week)
   - Pre-execution code scanning
   - Pattern matching for dangerous code
   - Automatic blocking

4. **Enhanced Monitoring** (3-5 days)
   - Execution logs per user
   - Cost tracking
   - Alert system

Once these four components are in place, you can safely remove IP whitelisting.

## Conclusion

The current IP-whitelisting approach is a pragmatic security measure during early development. The platform already has strong foundational security (gVisor, container isolation) that will serve well for public access.

The key insight is that **IP whitelisting is just buying time** to implement proper user management and abuse prevention. Once you have:
- Authentication to identify users
- Quotas to limit damage
- Abuse detection to block attacks
- Monitoring to detect problems

You can confidently open access to the research community. The existing container security means even malicious code can't escape the sandbox—you just need to prevent resource exhaustion and platform abuse.