# Git Tagging Strategy for Level-Based Development

## Overview

This document explains our git tagging approach for the iterative buildup development and demo presentation.

## Basic Tagging Workflow

### Creating Tags During Development

```bash
# Complete work on a level
git add .
git commit -m "Level 3: Establish async workflow with monitoring"
git tag level3-workflow

# Push tags to remote
git push origin --tags
```

### Viewing and Navigating Tags

```bash
# List all level tags
git tag -l "level*"

# List with creation dates
git tag -l "level*" --sort=-creatordate

# Checkout a specific level (detached HEAD - perfect for demos!)
git checkout level3-workflow

# Return to main branch
git checkout main
```

### Demo/Presentation Usage

```bash
# During presentation, simply checkout each level
git checkout level1-understanding
# Show/explain this level
git checkout level2-vocabulary
# Show progression
```

## Handling Updates to Earlier Levels

When you discover bugs or improvements needed in earlier levels, you have several options:

### Option 1: Document and Fix Forward (Recommended)

```bash
# Stay on main, fix the bug
git commit -m "Fix validation bug discovered in level 5 (present since level 2)"

# Add note to documentation
echo "Note: Validation bug fixed in level 5 was present since level 2" >> DEMO.md
```

**Pros**: 
- Shows realistic development process
- No history rewriting
- Simple and linear

**Cons**: 
- Earlier checkpoints contain known bugs

### Option 2: Versioned Tags

```bash
# Create fix branch from original tag
git checkout -b fix-level2 level2-vocabulary
git commit -m "Fix validation bug"
git tag level2-vocabulary-v2

# Document current versions
echo "level2-vocabulary-v2 ← CURRENT" >> DEMO.md
```

**Pros**: 
- Clean demo checkpoints
- Preserves original history

**Cons**: 
- Need to track which version is current

### Option 3: Branch per Level (Not Recommended)

```bash
# Create branch for each level
git checkout -b level1 <commit>
git tag level1-complete

# For fixes, just update the branch
git checkout level1
git commit -m "Fix bug"
# No new tag needed, branch HEAD is always "latest"
```

**Pros**: 
- Branch HEAD always points to latest
- No version management

**Cons**: 
- Branches meant for active development, not static points
- More complex branch management
- Tags are literally designed for this use case

## Tag Naming Conventions

### Basic Scheme
```
level<N>-<description>
```

Examples:
- `level1-understanding`
- `level2-vocabulary`
- `level3-workflow`

### With Versions (if needed)
```
level<N>-<description>-v<version>
```

Examples:
- `level2-vocabulary-v2`
- `level3-workflow-final`

### Alternative: Date-based
```
level<N>-<description>-<YYYY-MM-DD>
```

Examples:
- `level2-vocabulary-2024-01-15`

## Exporting Levels for Side-by-Side Comparison

If you want multiple levels available simultaneously:

```bash
# Export specific levels to folders
git archive level3-workflow --prefix=demo/level3/ | tar -x
git archive level5-mvp --prefix=demo/level5/ | tar -x

# Now you have:
demo/
  level3/
    src/
    README.md
  level5/
    src/
    README.md
```

## Common Git States Explained

### Detached HEAD
When you `git checkout <tag>` or `git checkout <commit>`:
- You're not on any branch
- HEAD points directly to a commit
- Perfect for read-only demo viewing
- Any commits made here will be "floating" (not on a branch)

```
1 --- 2 --- 3 --- 4 --- 5 --- 6 (main)
            ^
           HEAD (detached at level1-complete tag)
```

### Branch vs Tag
- **Branch**: Pointer that moves with new commits
- **Tag**: Permanent pointer to specific commit
- Tags are ideal for marking "milestones" or "checkpoints"

## Best Practices for This Project

1. **Use simple tags initially**: `level1-understanding`, `level2-vocabulary`
2. **Document known issues**: Add a `DEMO_NOTES.md` if bugs discovered later
3. **Test demo flow**: Before presentation, run through all checkouts
4. **Keep it realistic**: Bugs discovered later are part of the learning story

## Quick Reference

```bash
# Development flow
git commit -m "Complete level 3"
git tag level3-workflow
git push origin --tags

# Demo flow  
git checkout level1-understanding  # Start demo
git checkout level2-vocabulary     # Show progression
git checkout level3-workflow       # Continue story
git checkout main                  # Return to latest

# If fixes needed
# Option 1: Just document it
echo "Bug in level 2 was fixed in level 5" >> DEMO_NOTES.md

# Option 2: Create updated version
git checkout -b fix level2-vocabulary
git commit -m "Fix bug"
git tag level2-vocabulary-v2
```

## Advantages of This Approach

1. **Clean narrative**: Each level represents your thinking at that time
2. **Easy navigation**: Simple checkout commands during demo
3. **Realistic**: Shows how architecture actually evolves
4. **No overthinking**: Detached HEAD is fine for demos
5. **Git-native**: Using git as designed, not fighting it

## Summary

For this demo/learning project, simple tags with occasional versioning provides the best balance of:
- Easy development workflow
- Clean demo presentation  
- Realistic evolution story
- Minimal complexity

The key insight: embrace that architecture evolves. Bugs found later are part of the learning narrative, not failures to hide.