import fs from 'fs/promises'
import path from 'path'
import { templateMetadata, type TemplateMetadata } from './metadata'

export interface CodeTemplate extends TemplateMetadata {
  code: string
}

/**
 * Load a single template by ID (server-side only)
 */
export async function loadTemplate(id: string): Promise<CodeTemplate | null> {
  const metadata = templateMetadata.find(t => t.id === id)
  if (!metadata) {
    return null
  }

  try {
    const filePath = path.join(process.cwd(), 'lib', 'templates', metadata.filename)
    const code = await fs.readFile(filePath, 'utf-8')

    return {
      ...metadata,
      code,
    }
  } catch (error) {
    console.error(`Error loading template ${id}:`, error)
    return null
  }
}

/**
 * Load all templates (server-side only)
 */
export async function loadAllTemplates(): Promise<CodeTemplate[]> {
  const templates = await Promise.all(templateMetadata.map(meta => loadTemplate(meta.id)))

  return templates.filter((t): t is CodeTemplate => t !== null)
}

/**
 * Get templates by category
 */
export async function getTemplatesByCategory(): Promise<Record<string, CodeTemplate[]>> {
  const templates = await loadAllTemplates()

  return templates.reduce(
    (acc, template) => {
      const category = template.category
      if (!acc[category]) {
        acc[category] = []
      }
      acc[category]!.push(template)
      return acc
    },
    {} as Record<string, CodeTemplate[]>
  )
}
