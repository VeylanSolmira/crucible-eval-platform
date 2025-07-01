#!/usr/bin/env ts-node

/**
 * Analyzes all documentation files to find missing wiki links
 * Generates a report with actionable suggestions
 */

import { writeFileSync } from 'fs'
import * as path from 'path'
import { TopicDetector } from './topic-detector'
import { getAllDocs } from '../docs'

interface MissingLink {
  file: string
  line: number
  column: number
  text: string
  suggestedLink: string
  confidence: 'high' | 'medium' | 'low'
  reason: string
}

interface FileReport {
  path: string
  missingLinks: MissingLink[]
  hasIncomingLinks: boolean
  outgoingLinks: string[]
}

interface AnalysisReport {
  summary: {
    totalFiles: number
    filesWithMissingLinks: number
    totalMissingLinks: number
    orphanedFiles: number
    highConfidenceLinks: number
    mediumConfidenceLinks: number
    lowConfidenceLinks: number
  }
  fileReports: FileReport[]
  orphanedFiles: string[]
  topMissingTerms: Array<{ term: string; count: number }>
}

async function analyzeWikiLinks(): Promise<AnalysisReport> {
  console.log('🔍 Analyzing wiki links across all documentation...\n')
  
  // Get all documents
  const docs = await getAllDocs()
  const detector = new TopicDetector(docs, {
    enableAutoLink: false, // We're just analyzing, not modifying
    skipCodeBlocks: true,
    skipUrls: true,
    skipExistingLinks: true,
    maxLinksPerTerm: 10 // Higher limit for analysis
  })
  
  // Track incoming links
  const incomingLinks = new Map<string, Set<string>>()
  
  // Analyze each document
  const fileReports: FileReport[] = []
  const missingTermCounts = new Map<string, number>()
  
  for (const doc of docs) {
    console.log(`  Analyzing: ${doc.slug}`)
    
    const content = doc.content
    const lines = content.split('\n')
    const missingLinks: MissingLink[] = []
    const outgoingLinks: string[] = []
    
    // Find existing wiki links
    const existingLinkPattern = /\[\[([^\]]+)\]\]/g
    let match
    while ((match = existingLinkPattern.exec(content)) !== null) {
      const linkedDoc = match[1]
      if (linkedDoc) {
        outgoingLinks.push(linkedDoc)
        
        // Track incoming link
        if (!incomingLinks.has(linkedDoc)) {
          incomingLinks.set(linkedDoc, new Set())
        }
        incomingLinks.get(linkedDoc)!.add(doc.slug)
      }
    }
    
    // Detect missing links
    const topics = detector.detectTopics(content)
    
    topics.forEach(topic => {
      // Skip if this term is already linked somewhere in the doc
      if (content.includes(`[[${topic.canonical}]]`)) {
        return
      }
      
      // Find line number for first occurrence
      topic.positions.slice(0, 3).forEach(pos => { // Top 3 occurrences
        let line = 1
        let column = 1
        let currentPos = 0
        
        for (let i = 0; i < lines.length; i++) {
          const currentLine = lines[i]
          if (currentLine !== undefined && currentPos + currentLine.length >= pos.start) {
            line = i + 1
            column = pos.start - currentPos + 1
            break
          }
          currentPos += (currentLine?.length || 0) + 1 // +1 for newline
        }
        
        missingLinks.push({
          file: doc.slug,
          line,
          column,
          text: content.slice(pos.start, pos.end),
          suggestedLink: topic.canonical,
          confidence: topic.confidence,
          reason: getReasonForSuggestion(topic.canonical, topic.confidence)
        })
        
        // Track missing term counts
        missingTermCounts.set(
          topic.canonical,
          (missingTermCounts.get(topic.canonical) || 0) + 1
        )
      })
    })
    
    fileReports.push({
      path: doc.slug,
      missingLinks,
      hasIncomingLinks: false, // Will update after
      outgoingLinks
    })
  }
  
  // Update incoming links status
  fileReports.forEach(report => {
    report.hasIncomingLinks = incomingLinks.has(report.path)
  })
  
  // Find orphaned files
  const orphanedFiles = fileReports
    .filter(r => !r.hasIncomingLinks && r.path !== 'index')
    .map(r => r.path)
  
  // Get top missing terms
  const topMissingTerms = Array.from(missingTermCounts.entries())
    .sort((a, b) => b[1] - a[1])
    .slice(0, 20)
    .map(([term, count]) => ({ term, count }))
  
  // Calculate summary
  const allMissingLinks = fileReports.flatMap(r => r.missingLinks)
  const summary = {
    totalFiles: fileReports.length,
    filesWithMissingLinks: fileReports.filter(r => r.missingLinks.length > 0).length,
    totalMissingLinks: allMissingLinks.length,
    orphanedFiles: orphanedFiles.length,
    highConfidenceLinks: allMissingLinks.filter(l => l.confidence === 'high').length,
    mediumConfidenceLinks: allMissingLinks.filter(l => l.confidence === 'medium').length,
    lowConfidenceLinks: allMissingLinks.filter(l => l.confidence === 'low').length
  }
  
  return {
    summary,
    fileReports: fileReports.filter(r => r.missingLinks.length > 0 || !r.hasIncomingLinks),
    orphanedFiles,
    topMissingTerms
  }
}

function getReasonForSuggestion(term: string, confidence: string): string {
  const reasons: Record<string, string> = {
    'Crucible': 'Core platform name should always be linked',
    'METR': 'Organization name should be linked for context',
    'Docker': 'Key technology - link to Docker documentation',
    'Kubernetes': 'Important future platform - link to K8s docs',
    'gVisor': 'Critical security component - link to setup guide',
    'Container Isolation': 'Core security concept - must be linked',
    'AWS': 'Primary cloud platform - link to AWS docs',
    'EC2': 'Deployment target - link to EC2 guide',
    'FastAPI': 'Backend framework - link to API docs',
    'Next.js': 'Frontend framework - link to frontend docs',
    'TypeScript': 'Primary language - link to type safety docs'
  }
  
  return reasons[term] || `${confidence} priority term for wiki linking`
}

function generateMarkdownReport(report: AnalysisReport): string {
  const now = new Date().toISOString()
  
  let markdown = `# Wiki Missing Links Analysis Report

Generated: ${now}

## Executive Summary

- **Total Documentation Files**: ${report.summary.totalFiles}
- **Files with Missing Links**: ${report.summary.filesWithMissingLinks}
- **Total Missing Link Opportunities**: ${report.summary.totalMissingLinks}
- **Orphaned Files** (no incoming links): ${report.summary.orphanedFiles}

### Missing Links by Confidence
- 🔴 **High Confidence**: ${report.summary.highConfidenceLinks} (should definitely be linked)
- 🟡 **Medium Confidence**: ${report.summary.mediumConfidenceLinks} (consider linking)
- 🟢 **Low Confidence**: ${report.summary.lowConfidenceLinks} (optional)

## Top Missing Terms

These terms appear frequently but aren't consistently linked:

| Term | Occurrences | Priority |
|------|-------------|----------|
${report.topMissingTerms.map(t => `| ${t.term} | ${t.count} | ${getTermPriority(t.term)} |`).join('\n')}

## Orphaned Documents

These documents have no incoming wiki links and may be hard to discover:

${report.orphanedFiles.map(f => `- \`${f}\` - Consider linking from related documents`).join('\n')}

## Missing Links by File

`
  
  // Group by high priority files first
  const highPriorityFiles = report.fileReports
    .filter(r => r.missingLinks.some(l => l.confidence === 'high'))
    .sort((a, b) => b.missingLinks.length - a.missingLinks.length)
  
  const otherFiles = report.fileReports
    .filter(r => !r.missingLinks.some(l => l.confidence === 'high'))
    .sort((a, b) => b.missingLinks.length - a.missingLinks.length)
  
  if (highPriorityFiles.length > 0) {
    markdown += `### 🔴 High Priority Files\n\n`
    highPriorityFiles.forEach(file => {
      markdown += formatFileReport(file, true)
    })
  }
  
  if (otherFiles.length > 0) {
    markdown += `### Other Files\n\n`
    otherFiles.forEach(file => {
      markdown += formatFileReport(file, false)
    })
  }
  
  markdown += `
## Recommendations

1. **Immediate Actions**:
   - Add wiki links for all high-confidence terms (${report.summary.highConfidenceLinks} links)
   - Link to orphaned documents from relevant pages
   - Focus on core terms: Crucible, METR, Docker, gVisor, Container Isolation

2. **Quick Wins**:
   - Enable auto-linking for Tier 1 terms
   - Add "See Also" sections to orphaned documents
   - Create topic hub pages for frequently referenced concepts

3. **Future Improvements**:
   - Implement auto-linking during build process
   - Add link suggestions in documentation editor
   - Create visualization of document relationships

## How to Fix

To add a wiki link, use double square brackets:
\`\`\`markdown
The [[Crucible]] platform uses [[Docker]] for containerization.
\`\`\`

For links with custom text:
\`\`\`markdown
Our [[Container Isolation|isolation strategy]] prevents escapes.
\`\`\`
`
  
  return markdown
}

function formatFileReport(file: FileReport, showAll: boolean): string {
  let output = `#### \`${file.path}\`\n\n`
  
  if (!file.hasIncomingLinks) {
    output += `⚠️ **No incoming links** - This document is orphaned\n\n`
  }
  
  if (file.missingLinks.length > 0) {
    const links = showAll ? file.missingLinks : file.missingLinks.slice(0, 5)
    const confidence = { high: '🔴', medium: '🟡', low: '🟢' }
    
    output += `| Line | Text | Suggested Link | Priority |\n`
    output += `|------|------|----------------|----------|\n`
    
    links.forEach(link => {
      output += `| ${link.line} | "${link.text}" | [[${link.suggestedLink}]] | ${confidence[link.confidence]} |\n`
    })
    
    if (file.missingLinks.length > links.length) {
      output += `\n*... and ${file.missingLinks.length - links.length} more missing links*\n`
    }
  }
  
  output += '\n'
  return output
}

function getTermPriority(term: string): string {
  const highPriority = ['Crucible', 'METR', 'Docker', 'gVisor', 'Container Isolation']
  const mediumPriority = ['AWS', 'EC2', 'Kubernetes', 'FastAPI', 'Next.js']
  
  if (highPriority.includes(term)) return '🔴 High'
  if (mediumPriority.includes(term)) return '🟡 Medium'
  return '🟢 Low'
}

// Run the analysis
async function main() {
  try {
    const report = await analyzeWikiLinks()
    const markdown = generateMarkdownReport(report)
    
    // Save report
    const outputPath = path.join(process.cwd(), 'docs', 'wiki-missing-links-report.md')
    writeFileSync(outputPath, markdown)
    
    console.log(`\n✅ Analysis complete!`)
    console.log(`📄 Report saved to: ${outputPath}`)
    console.log(`\n📊 Summary:`)
    console.log(`   - ${report.summary.totalMissingLinks} missing link opportunities found`)
    console.log(`   - ${report.summary.orphanedFiles} orphaned documents detected`)
    console.log(`   - ${report.summary.highConfidenceLinks} high-priority links to add`)
    
  } catch (error) {
    console.error('❌ Error analyzing wiki links:', error)
    process.exit(1)
  }
}

// Allow running as a script
if (require.main === module) {
  void main()
}