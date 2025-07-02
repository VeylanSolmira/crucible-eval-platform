import { WikiProcessor, type BacklinkReference } from './wiki-processor'
import { getAllDocs } from '../docs'

let cachedProcessor: WikiProcessor | null = null
let cacheTime: number = 0
const CACHE_DURATION = 5 * 60 * 1000 // 5 minutes

/**
 * Process all documents to build backlinks index
 * This runs on the server during build time
 */
export async function getBacklinksForDoc(slug: string): Promise<BacklinkReference[]> {
  const now = Date.now()

  // Use cached processor if available and not stale
  if (cachedProcessor && now - cacheTime < CACHE_DURATION) {
    return cachedProcessor.getBacklinks(slug)
  }

  // Load all docs and process
  const allDocs = await getAllDocs()
  const existingSlugs = new Set(allDocs.map(d => d.slug))

  const processor = new WikiProcessor({
    pageResolver: (title: string) => [title.toLowerCase().replace(/\s+/g, '-')],
    hrefTemplate: (slug: string) => `/docs/${slug}`,
    pageExists: (slug: string) => existingSlugs.has(slug),
  })

  // Process all documents
  processor.processDocuments(allDocs)

  // Cache for future requests
  cachedProcessor = processor
  cacheTime = now

  return processor.getBacklinks(slug)
}
