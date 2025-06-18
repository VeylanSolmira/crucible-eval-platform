#!/bin/bash
# Weekly security audit script

set -e

echo "🔐 Running Weekly Security Audit"
echo "================================"

# 1. Dependency vulnerabilities
echo -e "\n📦 Checking npm dependencies..."
npm audit
echo "Dependency check complete."

# 2. Check for outdated packages
echo -e "\n📊 Checking for outdated packages..."
npx npm-check-updates

# 3. License compliance
echo -e "\n📜 Checking licenses..."
npx license-checker --summary

# 4. Security headers test (if running)
if lsof -Pi :3000 -sTCP:LISTEN -t >/dev/null ; then
    echo -e "\n🌐 Testing security headers..."
    curl -s -I http://localhost:3000 | grep -E "(X-Frame-Options|X-Content-Type-Options|X-XSS-Protection)"
fi

# 5. Check for exposed secrets
echo -e "\n🔍 Scanning for secrets..."
# Using git secrets or trufflehog if available
if command -v trufflehog &> /dev/null; then
    trufflehog filesystem . --exclude-paths=node_modules,.next
else
    echo "Install trufflehog for secret scanning: brew install trufflehog"
fi

# 6. TypeScript strict mode verification
echo -e "\n📝 Verifying TypeScript strict mode..."
grep -q '"strict": true' tsconfig.json && echo "✅ Strict mode enabled" || echo "❌ Strict mode disabled!"

# 7. Bundle size check
echo -e "\n📏 Checking bundle size..."
if [ -d ".next" ]; then
    du -sh .next/static
fi

echo -e "\n✅ Security audit complete!"
echo "Next audit due: $(date -d '+7 days' '+%Y-%m-%d')"