#!/bin/bash
# Check AWS Free Tier eligibility and usage

echo "=== AWS Free Tier Status Check ==="

# Method 1: Try to get account creation from various sources
echo -n "Checking account age... "

# Try Organizations API (works if part of an organization)
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
ACCOUNT_DATE=$(aws organizations describe-account --account-id $ACCOUNT_ID --query 'Account.JoinedTimestamp' --output text 2>/dev/null)

# If not in organization, try EC2 (look for earliest instance)
if [ -z "$ACCOUNT_DATE" ] || [ "$ACCOUNT_DATE" == "None" ]; then
    ACCOUNT_DATE=$(aws ec2 describe-instances --query 'Reservations[*].Instances[*].LaunchTime' --output text | sort | head -n1)
fi

# If we found a date, calculate age
if [ ! -z "$ACCOUNT_DATE" ] && [ "$ACCOUNT_DATE" != "None" ]; then
    # Convert to seconds since epoch (works on both Linux and Mac)
    if [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS
        ACCOUNT_EPOCH=$(date -j -f "%Y-%m-%dT%H:%M:%S" "${ACCOUNT_DATE%%.*}" +%s 2>/dev/null)
    else
        # Linux
        ACCOUNT_EPOCH=$(date -d "${ACCOUNT_DATE}" +%s 2>/dev/null)
    fi
    
    if [ ! -z "$ACCOUNT_EPOCH" ]; then
        CURRENT_EPOCH=$(date +%s)
        DAYS_OLD=$(( (CURRENT_EPOCH - ACCOUNT_EPOCH) / 86400 ))
        
        echo "Account is approximately $DAYS_OLD days old"
        
        if [ $DAYS_OLD -lt 365 ]; then
            echo "✅ Likely still in 12-month free tier"
        else
            echo "❌ Likely past 12-month free tier period"
        fi
    else
        echo "Could not parse date"
    fi
else
    echo "Could not determine account age"
fi

# Method 2: Check current costs (good indicator)
echo -e "\n=== Current Month AWS Costs ==="
CURRENT_COST=$(aws ce get-cost-and-usage \
    --time-period Start=$(date -u +%Y-%m-01),End=$(date -u +%Y-%m-%d) \
    --granularity MONTHLY \
    --metrics "UnblendedCost" \
    --query 'ResultsByTime[0].Total.UnblendedCost.Amount' \
    --output text 2>/dev/null)

if [ ! -z "$CURRENT_COST" ]; then
    echo "Current month cost: \$$CURRENT_COST USD"
    if (( $(echo "$CURRENT_COST < 1.0" | bc -l) )); then
        echo "✅ Low costs suggest free tier is active"
    fi
else
    echo "Could not retrieve cost data"
fi

# Method 3: Check current EC2 usage
echo -e "\n=== Current EC2 Usage ==="
aws ec2 describe-instances \
    --query 'Reservations[*].Instances[?State.Name==`running`].[InstanceId,InstanceType,LaunchTime,State.Name]' \
    --output table

# Count t2.micro and t3.micro hours
MICRO_INSTANCES=$(aws ec2 describe-instances \
    --query 'Reservations[*].Instances[?State.Name==`running` && (InstanceType==`t2.micro` || InstanceType==`t3.micro`)].InstanceId' \
    --output text | wc -w | xargs)

if [ "$MICRO_INSTANCES" -gt 0 ]; then
    echo -e "\nYou have $MICRO_INSTANCES t2/t3.micro instances running"
    HOURS_PER_MONTH=$((MICRO_INSTANCES * 744))
    echo "Estimated monthly usage: $HOURS_PER_MONTH hours (Free tier: 750 hours)"
    
    if [ $HOURS_PER_MONTH -gt 750 ]; then
        EXCESS=$((HOURS_PER_MONTH - 750))
        echo "⚠️  WARNING: Exceeding free tier by $EXCESS hours"
    else
        echo "✅ Within free tier limits"
    fi
fi

# Method 4: Direct link to console
echo -e "\n=== Check Detailed Free Tier Usage ==="
echo "For the most accurate information, visit:"
echo "https://console.aws.amazon.com/billing/home#/freetier"
echo ""
echo "Or run: open 'https://console.aws.amazon.com/billing/home#/freetier'"

# Additional tips
echo -e "\n=== Free Tier Tips ==="
echo "• t3.micro is better than t2.micro (2 vCPUs vs 1, same free tier)"
echo "• 750 hours/month = run 1 instance 24/7 OR multiple instances part-time"
echo "• Free tier includes: 30GB EBS, 5GB S3, 15GB bandwidth"
echo "• Set billing alerts: 'aws budgets create-budget'"