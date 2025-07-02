const fs = require('fs')
const path = require('path')
const { glob } = require('glob')

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
  'TypeScript',
]

async function analyzeWikiLinks() {
  console.log('🔍 Analyzing wiki links...\n')

  // Find all markdown files
  const docFiles = await glob('**/*.md', {
    cwd: path.join(__dirname, '../docs'),
    ignore: ['**/node_modules/**'],
  })

  const frontendFiles = await glob('**/*.md', {
    cwd: path.join(__dirname, 'docs'),
    ignore: ['**/node_modules/**'],
  })

  const allFiles = [
    ...docFiles.map(f => ({ path: `../docs/${f}`, relative: f })),
    ...frontendFiles.map(f => ({ path: `docs/${f}`, relative: `frontend/docs/${f}` })),
  ]

  console.log(`Found ${allFiles.length} documentation files\n`)

  const missingLinks = []
  const orphanedFiles = []
  const incomingLinks = new Map()

  // Analyze each file
  for (const file of allFiles) {
    const content = fs.readFileSync(path.join(__dirname, file.path), 'utf-8')
    const lines = content.split('\n')

    // Track existing wiki links
    const wikiLinks = content.match(/\[\[([^\]]+)\]\]/g) || []
    wikiLinks.forEach(link => {
      const target = link.slice(2, -2)
      if (!incomingLinks.has(target)) {
        incomingLinks.set(target, new Set())
      }
      incomingLinks.get(target).add(file.relative)
    })

    // Check for missing high-priority links
    HIGH_PRIORITY_TERMS.forEach(term => {
      if (content.includes(`[[${term}]]`)) return

      const regex = new RegExp(`\\b${term}\\b`, 'g')
      const matches = [...content.matchAll(regex)]

      if (matches.length > 0) {
        const match = matches[0]
        let line = 1
        let pos = 0

        for (let i = 0; i < lines.length; i++) {
          if (pos + lines[i].length >= match.index) {
            line = i + 1
            break
          }
          pos += lines[i].length + 1
        }

        missingLinks.push({
          file: file.relative,
          line,
          term,
          context: content
            .slice(
              Math.max(0, match.index - 30),
              Math.min(content.length, match.index + term.length + 30)
            )
            .replace(/\n/g, ' ')
            .trim(),
        })
      }
    })
  }

  // Find orphaned files
  allFiles.forEach(file => {
    const hasIncoming = Array.from(incomingLinks.values()).some(links => links.has(file.relative))
    if (!hasIncoming && !file.relative.includes('index')) {
      orphanedFiles.push(file.relative)
    }
  })

  // Generate report
  let report = `# Wiki Missing Links Report

Generated: ${new Date().toISOString()}

## Summary
- **Files analyzed**: ${allFiles.length}
- **Missing high-priority links**: ${missingLinks.length}
- **Orphaned files**: ${orphanedFiles.length}

## Top Missing Terms
`

  const termCounts = {}
  missingLinks.forEach(link => {
    termCounts[link.term] = (termCounts[link.term] || 0) + 1
  })

  Object.entries(termCounts)
    .sort((a, b) => b[1] - a[1])
    .forEach(([term, count]) => {
      report += `- **${term}**: ${count} occurrences\n`
    })

  report += `\n## Missing Links (Top 30)\n\n`
  report += `| File | Line | Term | Context |\n`
  report += `|------|------|------|---------|\n`

  missingLinks.slice(0, 30).forEach(link => {
    report += `| \`${link.file}\` | ${link.line} | ${link.term} | "${link.context}" |\n`
  })

  if (missingLinks.length > 30) {
    report += `\n*... and ${missingLinks.length - 30} more missing links*\n`
  }

  report += `\n## Orphaned Files\n\nThese files have no incoming wiki links:\n\n`
  orphanedFiles.forEach(file => {
    report += `- \`${file}\`\n`
  })

  report += `\n## How to Fix

1. Add wiki links using double brackets: \`[[Term]]\`
2. For custom text: \`[[Actual Page|Display Text]]\`
3. Focus on high-priority terms first
4. Link to orphaned documents from related pages\n`

  // Save report
  const outputPath = path.join(__dirname, '../docs/wiki-missing-links-report.md')
  fs.writeFileSync(outputPath, report)

  console.log(`✅ Report generated: ${outputPath}\n`)
  console.log(`📊 Summary:`)
  console.log(`   - ${missingLinks.length} missing links found`)
  console.log(`   - ${orphanedFiles.length} orphaned files detected`)
  console.log(
    `   - Top missing term: ${Object.keys(termCounts)[0]} (${termCounts[Object.keys(termCounts)[0]]} occurrences)`
  )
}

// Run the analyzer
analyzeWikiLinks().catch(console.error)
