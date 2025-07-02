#!/usr/bin/env node

/**
 * Auto-link top terms in documentation files
 * Can be run in dry-run mode to preview changes
 */

const fs = require('fs')
const path = require('path')
const { glob } = require('glob')

// Top priority terms to auto-link
const AUTO_LINK_TERMS = {
  // Core platform
  Crucible: 'Crucible',
  METR: 'METR',

  // Technologies
  Docker: 'Docker',
  Kubernetes: 'Kubernetes',
  K8s: 'Kubernetes',
  AWS: 'AWS',
  EC2: 'AWS EC2',
  gVisor: 'gVisor',
  runsc: 'gVisor',
  FastAPI: 'FastAPI',
  'Next.js': 'Next.js',
  TypeScript: 'TypeScript',

  // Core concepts
  'Container Isolation': 'Container Isolation',
  'Threat Model': 'Threat Model',
  Microservices: 'Architecture/Microservices',
}

// Files to skip
const SKIP_FILES = [
  'wiki-missing-links-report.md',
  'wiki-topics-analysis.md',
  'wiki-autolink-config.md',
  'node_modules',
  '.git',
]

async function autoLinkDocs(options = {}) {
  const { dryRun = true, maxChangesPerFile = 5 } = options

  console.log(`🔗 Auto-linking documentation (${dryRun ? 'DRY RUN' : 'LIVE MODE'})\n`)

  // Find all markdown files
  const docPaths = [
    { base: '../docs', files: await glob('**/*.md', { cwd: path.join(__dirname, '../../docs') }) },
    { base: 'docs', files: await glob('**/*.md', { cwd: path.join(__dirname, '../docs') }) },
  ]

  let totalChanges = 0
  const changedFiles = []

  for (const { base, files } of docPaths) {
    for (const file of files) {
      // Skip certain files
      if (SKIP_FILES.some(skip => file.includes(skip))) continue

      const filePath = path.join(__dirname, '..', base, file)
      let content = fs.readFileSync(filePath, 'utf-8')
      const originalContent = content
      let fileChanges = 0

      // Track changes for reporting
      const changes = []

      // Process each term
      for (const [term, linkTarget] of Object.entries(AUTO_LINK_TERMS)) {
        // Skip if already has wiki links for this term
        if (content.includes(`[[${term}]]`) || content.includes(`[[${linkTarget}]]`)) {
          continue
        }

        // Create regex that matches the term but not if it's already in a link
        // Also skip if in code blocks or URLs
        const regex = new RegExp(
          `(?<!\\[\\[)(?<!\\]\\]|\\)|\\])\\b(${escapeRegex(term)})\\b(?!\\]\\])(?![^\\[]*\\]\\])(?![^\\(]*\\))`,
          'g'
        )

        let match
        let matches = []

        while ((match = regex.exec(content)) !== null) {
          // Skip if inside code block
          const beforeMatch = content.substring(0, match.index)
          const codeBlockCount = (beforeMatch.match(/```/g) || []).length
          if (codeBlockCount % 2 === 1) continue // Inside code block

          // Skip if inside inline code
          const lineStart = content.lastIndexOf('\n', match.index) + 1
          const lineEnd = content.indexOf('\n', match.index)
          const line = content.substring(lineStart, lineEnd === -1 ? content.length : lineEnd)
          const posInLine = match.index - lineStart

          // Check for backticks around the match
          let inInlineCode = false
          let backtickCount = 0
          for (let i = 0; i < posInLine; i++) {
            if (line[i] === '`') backtickCount++
          }
          if (backtickCount % 2 === 1) continue // Inside inline code

          matches.push(match)
        }

        // Apply changes (limited per file)
        for (let i = 0; i < Math.min(matches.length, maxChangesPerFile - fileChanges); i++) {
          const match = matches[i]
          const replacement = `[[${linkTarget}]]`

          // Record the change
          changes.push({
            term,
            position: match.index,
            line: content.substring(0, match.index).split('\n').length,
            context: content
              .substring(
                Math.max(0, match.index - 30),
                Math.min(content.length, match.index + term.length + 30)
              )
              .replace(/\n/g, ' ')
              .trim(),
          })

          // Apply the change
          content =
            content.substring(0, match.index) +
            replacement +
            content.substring(match.index + term.length)

          fileChanges++
          totalChanges++

          // Adjust future match positions
          const adjustment = replacement.length - term.length
          for (let j = i + 1; j < matches.length; j++) {
            matches[j].index += adjustment
          }
        }

        if (fileChanges >= maxChangesPerFile) break
      }

      // Save changes if not dry run
      if (fileChanges > 0) {
        if (!dryRun) {
          fs.writeFileSync(filePath, content)
        }

        changedFiles.push({
          file: path.join(base, file),
          changes,
          fileChanges,
        })

        console.log(`📝 ${path.join(base, file)} - ${fileChanges} changes`)
        changes.forEach(change => {
          console.log(`   Line ${change.line}: "${change.context}" → [[${change.term}]]`)
        })
        console.log('')
      }
    }
  }

  // Summary
  console.log('\n📊 Summary:')
  console.log(`   Total changes: ${totalChanges}`)
  console.log(`   Files modified: ${changedFiles.length}`)

  if (dryRun) {
    console.log('\n⚠️  This was a dry run. No files were modified.')
    console.log('   Run with --live to apply changes.')
  }

  return { totalChanges, changedFiles }
}

function escapeRegex(str) {
  return str.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
}

// CLI handling
if (require.main === module) {
  const args = process.argv.slice(2)
  const dryRun = !args.includes('--live')
  const maxChangesPerFile = 5

  autoLinkDocs({ dryRun, maxChangesPerFile }).catch(console.error)
}

module.exports = { autoLinkDocs }
