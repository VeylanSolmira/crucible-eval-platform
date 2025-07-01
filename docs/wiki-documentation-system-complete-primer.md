Wiki Documentation System - Complete Primer

  Let me break down everything we've built and
  where we are now:

  🎯 What We're Building

  A wiki-style documentation system for Crucible
  that:
  - Automatically links related concepts (like
  Wikipedia's blue links)
  - Shows backlinks (which pages reference this
  page)
  - Will eventually visualize document
  relationships as an interactive graph
  - Helps with learning AI safety concepts by
  showing connections

  📁 What We've Done So Far

  1. Wiki Link Syntax ([[Page Name]])

  - Markdown files can now use [[Docker 
  Security]] to link to other docs
  - The system automatically finds the matching
  document
  - Shows red links for pages that don't exist
  yet

  2. Backlinks System

  - Each document shows "Referenced by:" at the
  bottom
  - Lists all other documents that link to it
  - Shows context around each reference

  3. Documentation Sources

  We're pulling docs from three locations:
  - /docs/* - Main project documentation
  (security, architecture, etc.)
  - /frontend/docs/* - Frontend-specific docs
  - /infrastructure/**/*.md - Infrastructure
  markdown files

  4. Docker Integration

  - Modified Dockerfile to copy docs into the
  container
  - Fixed .dockerignore to allow markdown files
  - Docs are now available when running in Docker

  5. Topic Analysis

  Created comprehensive analysis of all
  documentation finding:
  - 204 total markdown files
  - Core topics: Crucible, METR, Docker, gVisor,
  Container Isolation
  - Already using wiki links: About 10 documents

  6. Auto-Linking System (What we're doing now)

  Building tools to:
  - Automatically detect when documents mention
  important terms
  - Suggest where wiki links should be added
  - Generate reports showing "missing links"

  🗂️ Files We Created

  1. wiki-processor.ts - Core engine that
  processes wiki links
  2. BacklinksSection.tsx - UI component showing
  backlinks
  3. topic-detector.ts - Detects terms that could
   be wiki links
  4. wiki-topics-analysis.md - List of all
  important terms
  5. wiki-autolink-config.md - Configuration for
  auto-linking
  6. glossary.md - A-Z glossary of all technical
  terms
  7. analyze-wiki.js - Script to find missing
  links

  🔍 Current Task: Missing Links Analyzer

  The analyzer will scan all 204 documents and
  report:
  - "Docker" mentioned 47 times but only linked 5
   times
  - "gVisor" mentioned 23 times but never linked
  - 15 documents have no incoming links
  (orphaned)

  This helps prioritize which links to add first.

  🚀 Why This Matters

  1. For Learning: New team members can follow
  concept connections
  2. For Security: See how security measures
  relate to each other
  3. For METR: Visualize AI safety concepts and
  their dependencies
  4. For You: Better understand the platform
  during interviews

  📊 Next Steps After Analyzer

  1. Immediate: Add missing links for top 10
  terms
  2. Short-term: Enable auto-linking for core
  terms
  3. Medium-term: Build interactive graph
  visualization
  4. Long-term: AI-powered link suggestions

  💡 The Big Picture

  We're transforming static markdown files into
  an interconnected knowledge graph. When
  complete, you'll be able to:
  - Click through related concepts naturally
  - See a visual map of how everything connects
  - Never miss important relationships
  - Have AI suggest new connections