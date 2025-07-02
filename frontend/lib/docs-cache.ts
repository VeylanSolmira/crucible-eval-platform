import fs from 'fs'
import path from 'path'
import matter from 'gray-matter'

interface ProcessedDoc {
  frontmatter: Record<string, unknown>
  content: string
  hash: string
  path: string
}

let docsCache: Record<string, ProcessedDoc> | null = null

// Load preprocessed docs if available
function loadDocsCache(): Record<string, ProcessedDoc> {
  if (docsCache) return docsCache

  const cacheFile = path.join(process.cwd(), '.docs-cache', 'processed-docs.json')

  try {
    if (fs.existsSync(cacheFile)) {
      console.info('[Docs] Using preprocessed documentation cache')
      docsCache = JSON.parse(fs.readFileSync(cacheFile, 'utf8')) as Record<string, ProcessedDoc>
      return docsCache!
    }
  } catch {
    console.warn('[Docs] Failed to load preprocessed cache, falling back to runtime processing')
  }

  // Fallback to empty cache
  docsCache = {}
  return docsCache
}

// Get a processed doc from cache or process it
export function getProcessedDoc(docPath: string): ProcessedDoc | null {
  const cache = loadDocsCache()

  // Check cache first
  if (cache[docPath]) {
    return cache[docPath]
  }

  // Fallback to runtime processing
  const fullPath = path.join(process.cwd(), 'docs', docPath)

  try {
    if (fs.existsSync(fullPath)) {
      const content = fs.readFileSync(fullPath, 'utf8')
      const { data, content: body } = matter(content)

      const processed: ProcessedDoc = {
        frontmatter: data,
        content: body,
        hash: '',
        path: docPath,
      }

      // Cache for this session
      cache[docPath] = processed

      return processed
    }
  } catch (error) {
    console.error(`[Docs] Failed to process ${docPath}:`, error)
  }

  return null
}

// Get all docs from cache
export function getAllDocs(): ProcessedDoc[] {
  const cache = loadDocsCache()
  return Object.values(cache)
}
