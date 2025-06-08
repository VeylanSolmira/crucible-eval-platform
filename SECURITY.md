# Security Policy

## ⚠️ REPOSITORY VISIBILITY WARNING

**THIS REPOSITORY MUST REMAIN PRIVATE**

This repository contains:
- Interview preparation materials
- Proprietary system architecture designs
- Security-sensitive evaluation infrastructure details
- Personal development notes

## Before Making Public

If you ever need to make this repository public, you MUST:

1. **Remove all interview-related content**:
   - [ ] Delete `interview-prep.md`
   - [ ] Delete `metr-questions.md`
   - [ ] Delete `questions.md`
   - [ ] Delete `personal/` directory
   - [ ] Delete `CLAUDE.md` (contains personal notes)
   - [ ] Review and sanitize `docs/` directory

2. **Sanitize architecture documents**:
   - [ ] Remove any proprietary implementation details
   - [ ] Remove security-sensitive configurations
   - [ ] Remove internal network details

3. **Clean git history**:
   ```bash
   # Use BFG Repo-Cleaner or git filter-branch
   # to remove sensitive files from history
   ```

## Automated Checks

To add additional protection:

1. **GitHub Branch Protection Rules**:
   - Go to Settings → Branches
   - Add rule for `main` branch
   - Enable "Restrict who can push to matching branches"

2. **GitHub Repository Settings**:
   - Settings → Manage access → Base permissions: "No access"
   - Settings → Options → Disable "Allow merge commits" (optional)

3. **Local Git Hook** (see `.githooks/pre-push`)

## Contact

If you need to discuss making any part of this public, please contact the repository owner first.