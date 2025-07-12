# AWS Free Tier Guide

## Check Your Free Tier Usage

### 1. Check Current Free Tier Usage (AWS CLI)
```bash
# Shows your current month's free tier usage
aws ce get-cost-and-usage \
  --time-period Start=$(date -u +%Y-%m-01),End=$(date -u +%Y-%m-%d) \
  --granularity MONTHLY \
  --metrics "UsageQuantity" \
  --group-by Type=DIMENSION,Key=SERVICE \
  --filter file://free-tier-filter.json

# Create free-tier-filter.json:
{
  "Dimensions": {
    "Key": "USAGE_TYPE_GROUP",
    "Values": ["EC2: Running Hours", "RDS: Running Hours", "S3: Storage"]
  }
}
```

### 2. Better Option: Free Tier Dashboard
```bash
# Open the Free Tier dashboard in your browser
open https://console.aws.amazon.com/billing/home#/freetier

# Or get a direct link
echo "https://console.aws.amazon.com/billing/home#/freetier"
```

### 3. Check if Account is Still in 12-Month Free Tier
```bash
# Get account creation date
aws organizations describe-account --account-id $(aws sts get-caller-identity --query Account --output text) 2>/dev/null || \
aws iam get-user --query 'User.CreateDate' --output text

# Note: Free tier expires 12 months after account creation
```

## AWS Free Tier Types

### 1. **12-Month Free Tier** (Expires after first year)
- **EC2**: 750 hours/month of t2.micro or t3.micro
- **RDS**: 750 hours/month of db.t2.micro
- **EBS**: 30 GB of storage
- **S3**: 5 GB standard storage
- **CloudFront**: 50 GB data transfer out

### 2. **Always Free** (Never expires)
- **Lambda**: 1M requests/month
- **SNS**: 1M publishes
- **SQS**: 1M requests
- **DynamoDB**: 25 GB storage
- **CloudWatch**: 10 custom metrics

### 3. **Trials** (Short-term free usage)
- Various services with 30-90 day trials

## EC2 Free Tier Eligibility

### Eligible Instance Types (750 hours/month total)
```bash
# These share the 750 hour pool:
- t2.micro (1 vCPU, 1 GB RAM)
- t3.micro (2 vCPU, 1 GB RAM) ← Better choice!

# Important: 750 hours = ~31 days
# You can run 1 instance 24/7 OR multiple instances part-time
```

### Check Your EC2 Usage
```bash
# Current month's EC2 hours
aws ce get-cost-and-usage \
  --time-period Start=$(date -u +%Y-%m-01),End=$(date -u +%Y-%m-%d) \
  --granularity DAILY \
  --metrics "UsageQuantity" \
  --filter '{
    "Dimensions": {
      "Key": "SERVICE",
      "Values": ["Amazon Elastic Compute Cloud - Compute"]
    }
  }' \
  --group-by Type=DIMENSION,Key=USAGE_TYPE
```

## Checking Eligibility with Pricing API
```bash
# Check if an instance type is free tier eligible
aws pricing get-products \
  --service-code AmazonEC2 \
  --filters \
    "Type=TERM_MATCH,Field=instanceType,Value=t3.micro" \
    "Type=TERM_MATCH,Field=location,Value=US West (Oregon)" \
  --query 'PriceList[*]' \
  --output json | jq -r '.[] | fromjson | .terms.OnDemand[].priceDimensions[].description' | grep -i free

# Look for "free tier eligible" in the output
```

## Free Tier Best Practices

### 1. Set Up Billing Alerts
```bash
# Create a billing alarm for $1
aws cloudwatch put-metric-alarm \
  --alarm-name "FreeTierBillingAlert" \
  --alarm-description "Alert when AWS bill exceeds $1" \
  --metric-name EstimatedCharges \
  --namespace AWS/Billing \
  --statistic Maximum \
  --period 86400 \
  --threshold 1 \
  --comparison-operator GreaterThanThreshold \
  --datapoints-to-alarm 1 \
  --evaluation-periods 1 \
  --treat-missing-data notBreaching
```

### 2. Use Free Tier Calculator
```python
# Simple free tier calculator
def calculate_free_tier_remaining():
    """Calculate remaining free tier hours for current month"""
    import datetime
    
    now = datetime.datetime.now()
    days_in_month = 30  # Approximate
    days_elapsed = now.day
    days_remaining = days_in_month - days_elapsed
    
    # 750 hours total per month
    hours_remaining = (750 / days_in_month) * days_remaining
    
    print(f"Days remaining in month: {days_remaining}")
    print(f"Free tier hours remaining: {hours_remaining:.0f}")
    print(f"Can run 1 instance 24/7: {'Yes' if hours_remaining >= days_remaining * 24 else 'No'}")
    print(f"Can run 2 instances 24/7: {'Yes' if hours_remaining >= days_remaining * 48 else 'No'}")
```

## Cost-Effective Architecture for Free Tier

### Single Instance Strategy
```hcl
# terraform.tfvars
instance_type = "t3.micro"  # Better than t2.micro, same free tier
enable_k8s_single_node = true

# Uses your 750 hours/month wisely:
# - 1 t3.micro running 24/7 = 744 hours (within limit)
# - 2 vCPUs instead of 1 (t2.micro)
# - Newer generation, better performance
```

### Multi-Instance Strategy (Development)
```bash
# Run instances only when needed
Morning:  Start 2 instances (8 hours) = 16 hours
Evening:  Stop instances
Weekend:  Keep stopped

Monthly usage: 16 hours × 22 workdays = 352 hours (well under 750)
```

## Common Free Tier Mistakes

### 1. **Multiple Instances**
```bash
# WRONG: Running 2 t3.micro instances 24/7
2 instances × 744 hours = 1,488 hours (OVER LIMIT by 738 hours)
Cost: ~$5.40 for excess hours
```

### 2. **Wrong Region**
```bash
# Some regions don't have free tier
# Always check: US East (N. Virginia), US West (Oregon), EU (Ireland)
```

### 3. **Forgetting EBS Volumes**
```bash
# Free tier: 30 GB total EBS storage
# Each instance might have 20-30 GB root volume
# Multiple instances = exceeding storage limit
```

### 4. **Data Transfer**
```bash
# Free tier: 15 GB out/month (aggregated across services)
# Heavy Docker pulls, package updates can exceed this
```

## Monitoring Script
```bash
#!/bin/bash
# save as check-free-tier.sh

echo "=== AWS Free Tier Status Check ==="

# Get account age
ACCOUNT_DATE=$(aws iam get-user --query 'User.CreateDate' --output text 2>/dev/null || echo "Unknown")
echo "Account created: $ACCOUNT_DATE"

# Calculate if still in free tier (rough estimate)
if [ "$ACCOUNT_DATE" != "Unknown" ]; then
  ACCOUNT_EPOCH=$(date -j -f "%Y-%m-%dT%H:%M:%S" "${ACCOUNT_DATE%%.*}" +%s 2>/dev/null || date -d "${ACCOUNT_DATE}" +%s)
  CURRENT_EPOCH=$(date +%s)
  DAYS_OLD=$(( (CURRENT_EPOCH - ACCOUNT_EPOCH) / 86400 ))
  
  if [ $DAYS_OLD -lt 365 ]; then
    echo "✅ Still in 12-month free tier (${DAYS_OLD} days old)"
  else
    echo "❌ Free tier expired (${DAYS_OLD} days old)"
  fi
fi

# Check current EC2 usage
echo -e "\n=== Current EC2 Instances ==="
aws ec2 describe-instances \
  --query 'Reservations[*].Instances[?State.Name==`running`].[InstanceId,InstanceType,LaunchTime]' \
  --output table

# Get current month costs
echo -e "\n=== Current Month Costs ==="
aws ce get-cost-and-usage \
  --time-period Start=$(date -u +%Y-%m-01),End=$(date -u +%Y-%m-%d) \
  --granularity MONTHLY \
  --metrics "UnblendedCost" \
  --query 'ResultsByTime[0].Total.UnblendedCost' \
  --output json | jq -r '.Amount + " " + .Unit'

echo -e "\nFor detailed free tier usage, visit:"
echo "https://console.aws.amazon.com/billing/home#/freetier"
```

## Summary

1. **Check eligibility**: Your account must be < 12 months old
2. **Check usage**: Use AWS Console Free Tier page (easiest)
3. **Eligible resources**: t2.micro or t3.micro (750 hrs/month combined)
4. **Best practice**: Use t3.micro over t2.micro (same free tier, better specs)
5. **Monitor closely**: Set up billing alerts at $1, $5, $10
6. **Remember**: Free tier is per account, not per region