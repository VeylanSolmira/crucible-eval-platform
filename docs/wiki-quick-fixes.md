# Wiki Quick Fixes - Priority Manual Edits

Based on the missing links analysis, here are the highest-impact manual fixes to make:

## 🔴 Critical: Link Core Documentation

These foundational documents need incoming links to be discoverable:

### 1. **README.md** (Main entry point)
- Add to: `docs/index.md` or create one
- Link text: `[[README|Getting Started]]`
- Reason: Entry point for all users

### 2. **architecture.md** (System overview)  
- Add to: `README.md`, `getting-started/` docs
- Link text: `[[Architecture|Platform Architecture]]`
- Reason: Essential for understanding the system

### 3. **glossary.md** (Term definitions)
- Add to: All docs that use technical terms
- Link text: `[[Glossary]]`
- Reason: Central reference for all terms

### 4. **security/threat-model.md**
- Add to: `architecture.md`, security docs
- Link text: `[[Threat Model]]`
- Reason: Core security documentation

### 5. **deployment/ec2.md**
- Add to: `README.md`, deployment index
- Link text: `[[EC2 Deployment]]`
- Reason: Primary deployment method

## 🟡 Important: Fix Glossary Internal Links

The glossary mentions many terms but doesn't link them. Add these:

```markdown
### Docker
Container runtime providing process isolation. Enhanced with [[gVisor]] for additional security. See [[Docker Security]].

### Kubernetes (K8s)  
Container orchestration platform planned for future scaling. See [[Deployment/Kubernetes]].

### AWS (Amazon Web Services)
Primary cloud provider for Crucible infrastructure. Key services include [[EC2]], [[S3]], [[IAM]], and [[SQS]].
```

## 🟢 Quick Wins: Top Term Linking

Add these to the most-viewed documents:

### In `README.md`:
```markdown
The [[Crucible]] platform is built for [[METR]] to evaluate AI models safely using [[Docker]] containers with [[Container Isolation]].
```

### In `architecture.md`:
```markdown
## Overview
The [[Crucible]] platform uses a [[Microservices]] architecture deployed on [[AWS]] [[EC2]] instances, with plans to migrate to [[Kubernetes]].
```

### In `getting-started/quickstart.md`:
```markdown
1. Install [[Docker]] and Docker Compose
2. Configure [[AWS]] credentials  
3. Run the [[Crucible]] platform locally
```

## 📋 Checklist: Manual Fixes Priority Order

1. [ ] Create `docs/index.md` linking to README and major sections
2. [ ] Add links TO architecture.md from at least 5 documents
3. [ ] Fix glossary.md internal links (30+ terms)
4. [ ] Add [[Crucible]] and [[METR]] to all major documents
5. [ ] Link orphaned security documents from threat-model.md
6. [ ] Create "See Also" sections in orphaned docs
7. [ ] Add navigation links between related planning docs
8. [ ] Link deployment guides from architecture docs
9. [ ] Cross-reference all security documents
10. [ ] Add topic hub pages for Docker, Kubernetes, AWS

## 🎯 Expected Impact

After these fixes:
- **-180 orphaned documents** → ~20 orphaned
- **+343 navigation paths** from top 5 terms
- **Better discovery** of critical documentation
- **Clearer learning paths** for new team members

## 🔧 Tools to Help

1. Run auto-link script: `node frontend/scripts/auto-link-docs.js --live`
2. Re-run analyzer: `node frontend/analyze-wiki.js`
3. Check specific file: `grep -c "\[\[" docs/file.md`
4. Find unlinked mentions: `grep -n "Docker" docs/file.md | grep -v "\[\["`