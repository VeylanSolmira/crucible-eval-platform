# Slides Feature

This directory contains the presentation slides for the METR Evaluation Platform.

## Structure

- `*.md` - Individual slide files in Markdown format with frontmatter
- `index.json` - Metadata and index of all slides
- `README.md` - This file

## Slide Format

Each slide file uses Markdown with YAML frontmatter:

```markdown
---
title: 'Slide Title'
order: 1
tags: ['tag1', 'tag2']
description: 'Optional description'
---

# Main Title

Slide content here...

---

## Second Slide Section

More content...
```

Use `---` to separate individual slides within a file.

## Adding New Slides

1. Create a new `.md` file with a descriptive filename
2. Add frontmatter with title, order, and tags
3. Write your slide content using Markdown
4. Update `index.json` with the new slide metadata

## Viewing Slides

Navigate to `/slides` in the application to:

- Browse all slides
- View individual slides
- Present slides using reveal.js
- Edit slides with live preview

## Editing Slides

The slide editor supports:

- Live preview
- Syntax highlighting for code blocks
- Markdown formatting
- Frontmatter editing
