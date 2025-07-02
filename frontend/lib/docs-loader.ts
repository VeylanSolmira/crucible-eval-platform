/**
 * Optimized Document Loading Strategy
 *
 * Current: Static generation at build time
 * Future: Can migrate to API-based loading without changing components
 */

import { getDocsConfig } from './docs-config'
import { getDocBySlug, getAllDocs, type Doc } from './docs'

// Document loader interface - components use this, not direct file access
export interface DocumentLoader {
  loadDocument(slug: string[]): Promise<Doc | null>
  loadAllDocuments(): Promise<Doc[]>
  searchDocuments(query: string): Promise<Doc[]>
}

// Static loader - reads from filesystem at build time
class StaticDocumentLoader implements DocumentLoader {
  async loadDocument(slug: string[]): Promise<Doc | null> {
    // At build time, this reads from disk
    // In browser, this will be pre-loaded
    return getDocBySlug(slug)
  }

  async loadAllDocuments(): Promise<Doc[]> {
    return getAllDocs()
  }

  async searchDocuments(query: string): Promise<Doc[]> {
    const allDocs = await this.loadAllDocuments()
    const lowerQuery = query.toLowerCase()

    return allDocs.filter(
      doc =>
        doc.title.toLowerCase().includes(lowerQuery) ||
        doc.content.toLowerCase().includes(lowerQuery) ||
        (doc.description && doc.description.toLowerCase().includes(lowerQuery))
    )
  }
}

// Dynamic loader - fetches from API (future optimization)
class DynamicDocumentLoader implements DocumentLoader {
  private cache = new Map<string, Doc>()
  private cacheTimeout = 5 * 60 * 1000 // 5 minutes

  async loadDocument(slug: string[]): Promise<Doc | null> {
    const key = slug.join('/')

    // Check cache
    if (this.cache.has(key)) {
      return this.cache.get(key)!
    }

    // Fetch from API
    try {
      const response = await fetch(`/api/docs/${key}`)
      if (!response.ok) return null

      const doc = (await response.json()) as Doc
      this.cache.set(key, doc)

      // Clear cache after timeout
      setTimeout(() => this.cache.delete(key), this.cacheTimeout)

      return doc
    } catch (error) {
      console.error('Error loading document:', error)
      return null
    }
  }

  async loadAllDocuments(): Promise<Doc[]> {
    const response = await fetch('/api/docs')
    return response.json() as Promise<Doc[]>
  }

  async searchDocuments(query: string): Promise<Doc[]> {
    const response = await fetch(`/api/docs/search?q=${encodeURIComponent(query)}`)
    return response.json() as Promise<Doc[]>
  }
}

// Hybrid loader - uses static for known docs, dynamic for updates
class HybridDocumentLoader implements DocumentLoader {
  private static = new StaticDocumentLoader()
  private dynamic = new DynamicDocumentLoader()

  async loadDocument(slug: string[]): Promise<Doc | null> {
    // Try static first (fast)
    const staticDoc = await this.static.loadDocument(slug)
    if (staticDoc) return staticDoc

    // Fall back to dynamic (for new docs)
    return this.dynamic.loadDocument(slug)
  }

  async loadAllDocuments(): Promise<Doc[]> {
    // Always use dynamic for listing (to catch new docs)
    return this.dynamic.loadAllDocuments()
  }

  async searchDocuments(query: string): Promise<Doc[]> {
    // Use dynamic for search (server-side is faster)
    return this.dynamic.searchDocuments(query)
  }
}

// Factory function - returns appropriate loader based on config
export function createDocumentLoader(): DocumentLoader {
  const config = getDocsConfig()

  switch (config.loadingStrategy) {
    case 'dynamic':
      return new DynamicDocumentLoader()
    case 'hybrid':
      return new HybridDocumentLoader()
    case 'static':
    default:
      return new StaticDocumentLoader()
  }
}

// Default export for convenience
export const documentLoader = createDocumentLoader()
