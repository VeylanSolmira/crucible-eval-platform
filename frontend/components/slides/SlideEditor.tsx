'use client'

import { useState, useEffect } from 'react'
import type { Slide } from '@/lib/slides/loader'
import Editor from '@monaco-editor/react'

interface SlideEditorProps {
  slide: Slide
  onSave: (slide: Slide) => Promise<void>
  onCancel: () => void
}

export function SlideEditor({ slide, onSave, onCancel }: SlideEditorProps) {
  const [editedSlide, _setEditedSlide] = useState<Slide>(slide)
  const [content, setContent] = useState('')
  const [saving, setSaving] = useState(false)
  const [preview, setPreview] = useState(false)

  useEffect(() => {
    // Reconstruct the markdown content with frontmatter
    const frontmatter = `---
title: "${editedSlide.title}"
duration: ${editedSlide.duration}
tags: [${editedSlide.tags.map(t => `"${t}"`).join(', ')}]
${editedSlide.description ? `description: "${editedSlide.description}"` : ''}
---

${editedSlide.content}`

    setContent(frontmatter)
  }, [editedSlide])

  const handleSave = async () => {
    setSaving(true)
    try {
      // Parse the content to extract frontmatter and markdown
      const lines = content.split('\n')
      let inFrontmatter = false
      const frontmatterLines: string[] = []
      const markdownLines: string[] = []
      let frontmatterCount = 0

      for (const line of lines) {
        if (line === '---') {
          frontmatterCount++
          if (frontmatterCount === 2) {
            inFrontmatter = false
            continue
          } else if (frontmatterCount === 1) {
            inFrontmatter = true
            continue
          }
        }

        if (inFrontmatter) {
          frontmatterLines.push(line)
        } else if (frontmatterCount >= 2) {
          markdownLines.push(line)
        }
      }

      // Parse frontmatter
      interface FrontmatterData {
        title?: string
        duration?: number
        tags?: string[]
        description?: string
        [key: string]: string | number | string[] | undefined
      }

      const frontmatter: FrontmatterData = {}
      frontmatterLines.forEach(line => {
        const match = line.match(/^(\w+):\s*(.+)$/)
        if (match) {
          const key = match[1]!
          const rawValue = match[2]!.trim()
          let value: string | number | string[]

          // Parse different value types
          if (rawValue.startsWith('[') && rawValue.endsWith(']')) {
            // Array
            value = rawValue
              .slice(1, -1)
              .split(',')
              .map((v: string) => v.trim().replace(/^["']|["']$/g, ''))
          } else if (rawValue.startsWith('"') && rawValue.endsWith('"')) {
            // String
            value = rawValue.slice(1, -1)
          } else if (!isNaN(Number(rawValue))) {
            // Number
            value = Number(rawValue)
          } else {
            // Default to string
            value = rawValue
          }

          frontmatter[key] = value
        }
      })

      const markdown = markdownLines.join('\n').trim()
      const sections = markdown
        .split(/\n---\n/)
        .map(s => s.trim())
        .filter(Boolean)

      const updatedSlide: Slide = {
        ...editedSlide,
        title: frontmatter.title || editedSlide.title,
        duration: frontmatter.duration || editedSlide.duration,
        tags: Array.isArray(frontmatter.tags) ? frontmatter.tags : editedSlide.tags,
        ...(frontmatter.description !== undefined && { description: frontmatter.description }),
        content: markdown,
        sections,
      }

      await onSave(updatedSlide)
    } catch (error) {
      console.error('Error saving slide:', error)
      alert('Error saving slide. Please check the format.')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="slide-editor h-full flex flex-col">
      <div className="flex items-center justify-between p-4 border-b">
        <h2 className="text-xl font-semibold">Edit Slide: {editedSlide.title}</h2>
        <div className="flex gap-2">
          <button
            onClick={() => setPreview(!preview)}
            className="px-4 py-2 bg-gray-200 text-gray-800 rounded hover:bg-gray-300"
          >
            {preview ? 'Edit' : 'Preview'}
          </button>
          <button
            onClick={() => void handleSave()}
            disabled={saving}
            className="px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600 disabled:bg-blue-300"
          >
            {saving ? 'Saving...' : 'Save'}
          </button>
          <button
            onClick={onCancel}
            className="px-4 py-2 bg-gray-500 text-white rounded hover:bg-gray-600"
          >
            Cancel
          </button>
        </div>
      </div>

      <div className="flex-1 overflow-hidden">
        {preview ? (
          <div className="h-full p-8 overflow-y-auto">
            <div className="prose prose-lg max-w-none">
              <h1>{editedSlide.title}</h1>
              {editedSlide.sections.map((section, index) => (
                <div key={index} className="mb-8 pb-8 border-b last:border-0">
                  <div dangerouslySetInnerHTML={{ __html: section }} />
                </div>
              ))}
            </div>
          </div>
        ) : (
          <div className="h-full">
            <Editor
              height="100%"
              value={content}
              onChange={value => setContent(value || '')}
              language="markdown"
              theme="vs-dark"
              options={{
                wordWrap: 'on',
                minimap: { enabled: false },
                fontSize: 14,
                lineNumbers: 'on',
                rulers: [80],
                scrollBeyondLastLine: false,
              }}
            />
          </div>
        )}
      </div>

      <div className="p-4 bg-gray-100 text-sm">
        <p className="text-gray-600">
          Format: Use <code>---</code> to separate slides. First section should contain frontmatter
          with title, duration, tags, and optional description.
        </p>
      </div>
    </div>
  )
}
