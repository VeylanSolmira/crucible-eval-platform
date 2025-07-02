# Dependabot Guide

## What is Dependabot?

Dependabot is GitHub's automated dependency update tool that keeps your project secure and up-to-date.

## How It Works

### Monitoring

- Checks `package.json` on a schedule (we use weekly)
- Scans for security vulnerabilities 24/7
- Compares your versions to latest releases

### Automated PRs

Every Monday, Dependabot will:

1. Check all npm packages for updates
2. Create pull requests for outdated packages
3. Run CI/CD tests automatically
4. Group related updates (e.g., all TypeScript types)

### Example PR

```
Title: chore(deps): Bump next from 14.2.30 to 14.2.31

This PR updates next from 14.2.30 to 14.2.31
- [Release notes](https://github.com/vercel/next.js/releases)
- [Changelog](https://github.com/vercel/next.js/blob/canary/CHANGELOG.md)
- [Commits](https://github.com/vercel/next.js/compare/v14.2.30...v14.2.31)

Signed-off-by: dependabot[bot]
```

## Security Updates

**Critical Difference**: Security updates don't wait for Monday!

- Created immediately when vulnerability detected
- Labeled with `security` tag
- Should be reviewed and merged ASAP

## Alerts and Notifications

### Do you get pager alerts?

**No**, Dependabot doesn't page you at 3am. Instead:

1. **GitHub Notifications** - You'll get GitHub notifications for PRs
2. **Email Alerts** - If configured in your GitHub settings
3. **Security Tab** - Critical alerts appear in repo's Security tab
4. **Slack Integration** - Can configure GitHub → Slack for team alerts

For true pager-level alerts, you'd need:

```yaml
# Example: PagerDuty integration via GitHub Actions
name: Security Alert
on:
  pull_request:
    types: [opened]
jobs:
  alert:
    if: contains(github.event.pull_request.labels.*.name, 'security')
    runs-on: ubuntu-latest
    steps:
      - name: Page on critical security
        run: |
          # Send to PagerDuty/Opsgenie/etc
```

### Auto-merge?

**Not by default**, but you can enable it:

#### Option 1: GitHub Auto-merge (Safest)

```yaml
# In dependabot.yml
updates:
  - package-ecosystem: 'npm'
    # ... other config ...
    # Only auto-merge patch updates
    allow:
      - dependency-type: 'production'
        update-types: ['patch']
```

Then enable auto-merge in repo settings for Dependabot PRs.

#### Option 2: GitHub Actions (More Control)

```yaml
name: Auto-merge Dependabot
on: pull_request

jobs:
  auto-merge:
    runs-on: ubuntu-latest
    if: github.actor == 'dependabot[bot]'
    steps:
      - name: Auto-merge patch updates
        if: contains(github.event.pull_request.title, 'patch')
        run: gh pr merge --auto --squash "$PR_URL"
        env:
          PR_URL: ${{github.event.pull_request.html_url}}
          GITHUB_TOKEN: ${{secrets.GITHUB_TOKEN}}
```

#### Auto-merge Best Practices

1. **Only auto-merge patch versions** (1.2.3 → 1.2.4)
2. **Never auto-merge major versions** (1.x.x → 2.x.x)
3. **Require CI passing** before auto-merge
4. **Manual review for security updates** (even patches)

## Our Configuration

```yaml
# frontend/.github/dependabot.yml
version: 2
updates:
  - package-ecosystem: 'npm'
    directory: '/frontend'
    schedule:
      interval: 'weekly'
      day: 'monday'
    open-pull-requests-limit: 5
    groups:
      typescript:
        patterns: ['@types/*', 'typescript']
      react:
        patterns: ['react', 'react-dom', '@types/react*']
```

## Weekly Workflow

### Monday Morning Routine

1. Check GitHub for Dependabot PRs
2. Review changes (especially breaking changes)
3. Ensure CI is green
4. Merge safe updates
5. Test locally if concerned

### Priority Order

1. 🚨 **Security updates** - Merge immediately
2. 🐛 **Bug fixes** - Merge soon
3. ✨ **Features** - Review carefully
4. 📦 **Major versions** - Test thoroughly

## Benefits

1. **Security** - Immediate vulnerability notifications
2. **Maintenance** - No manual version checking
3. **Consistency** - Regular update cadence
4. **Testing** - All updates run through CI
5. **Grouping** - Reduces PR noise

## Troubleshooting

### PR Conflicts

```bash
# Rebase Dependabot PR
@dependabot rebase
```

### Ignore Update

```bash
# In PR comment
@dependabot ignore this major version
@dependabot ignore this dependency
```

### Re-create PR

```bash
# Force recreation
@dependabot recreate
```

## Summary

Dependabot = Your automated dependency janitor

- Won't wake you up at night
- Can auto-merge (with careful configuration)
- Keeps you secure without the hassle
