/**
 * Simple wiki link analyzer that can be run during build
 */

import { readFileSync } from 'fs'
import { globSync } from 'glob'
import * as path from 'path'

// High-priority terms that should always be linked
const HIGH_PRIORITY_TERMS = [
  'Crucible',
  'METR',
  'Docker',
  'Kubernetes',
  'K8s',
  'gVisor',
  'runsc',
  'Container Isolation',
  'AWS',
  'EC2',
  'FastAPI',
  'Next.js',
  'TypeScript'
]

interface MissingLink {
  file: string
  line: number
  text: string
  suggestedTerm: string
}

export function analyzeWikiLinks(docsPath: string = '../docs'): {
  missingLinks: MissingLink[]
  orphanedFiles: string[]
  summary: string
} {
  const files = globSync('**/*.md', {
    cwd: docsPath,
    ignore: ['**/node_modules/**', '**/README.md']
  })
  
  const missingLinks: MissingLink[] = []
  const fileGraph = new Map<string, Set<string>>() // file -> files it links to
  const incomingLinks = new Map<string, Set<string>>() // file -> files that link to it
  
  // Analyze each file
  files.forEach(file => {
    const content = readFileSync(path.join(docsPath, file), 'utf-8')
    const lines = content.split('\n')
    const outgoingLinks = new Set<string>()
    
    // Track existing wiki links
    const wikiLinkRegex = /\[\[([^\]]+)\]\]/g
    let match
    while ((match = wikiLinkRegex.exec(content)) !== null) {
      if (match[1]) {
        const linkedDoc = match[1].toLowerCase().replace(/\s+/g, '-')
        outgoingLinks.add(linkedDoc)
        
        if (!incomingLinks.has(linkedDoc)) {
          incomingLinks.set(linkedDoc, new Set())
        }
        incomingLinks.get(linkedDoc)!.add(file)
      }
    }
    
    fileGraph.set(file, outgoingLinks)
    
    // Check for missing high-priority links
    HIGH_PRIORITY_TERMS.forEach(term => {
      // Skip if already linked
      if (content.includes(`[[${term}]]`)) return
      
      // Find occurrences
      const termRegex = new RegExp(`\\b${term}\\b`, 'g')
      let termMatch
      while ((termMatch = termRegex.exec(content)) !== null) {
        // Find line number
        let lineNum = 1
        let pos = 0
        for (let i = 0; i < lines.length; i++) {
          const line = lines[i]
          if (line !== undefined && pos + line.length >= termMatch.index) {
            lineNum = i + 1
            break
          }
          pos += (line?.length || 0) + 1
        }
        
        missingLinks.push({
          file,
          line: lineNum,
          text: content.slice(
            Math.max(0, termMatch.index - 20),
            Math.min(content.length, termMatch.index + term.length + 20)
          ).trim(),
          suggestedTerm: term
        })
        
        break // Only report first occurrence per term per file
      }
    })
  })
  
  // Find orphaned files
  const orphanedFiles = files.filter(file => {
    const slug = file.replace(/\.md$/, '').toLowerCase()
    return !incomingLinks.has(slug) && !file.includes('index')
  })
  
  // Generate summary
  const summary = `
Wiki Link Analysis Summary:
- Files analyzed: ${files.length}
- Missing high-priority links: ${missingLinks.length}
- Orphaned documents: ${orphanedFiles.length}

Top missing terms:
${HIGH_PRIORITY_TERMS.map(term => {
  const count = missingLinks.filter(l => l.suggestedTerm === term).length
  return count > 0 ? `- ${term}: ${count} missing links` : null
}).filter(Boolean).join('\n')}
  `.trim()
  
  return { missingLinks, orphanedFiles, summary }
}

// Export for use in build scripts
export function generateReport(): string {
  const { missingLinks, orphanedFiles, summary } = analyzeWikiLinks()
  
  const report = `# Wiki Missing Links Report

${summary}

## Missing High-Priority Links

${missingLinks.slice(0, 50).map(link => 
  `- \`${link.file}:${link.line}\` - "${link.text}" → [[${link.suggestedTerm}]]`
).join('\n')}

${missingLinks.length > 50 ? `\n... and ${missingLinks.length - 50} more missing links\n` : ''}

## Orphaned Documents

${orphanedFiles.map(file => `- \`${file}\``).join('\n')}
`
  
  return report
}