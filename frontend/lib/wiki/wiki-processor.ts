/**
 * Wiki-style cross-reference and backlink processing
 */

import type { Doc } from '../docs'

export interface WikiLink {
  from: string // slug of source document
  to: string // slug or title of target
  text: string // display text
  exists: boolean // whether target exists
}

export interface BacklinkReference {
  fromSlug: string
  fromTitle: string
  context: string // surrounding text for context
}

export interface WikiProcessorOptions {
  // Convert page title to slug
  pageResolver?: (title: string) => string[]
  // Template for generating href
  hrefTemplate?: (slug: string) => string
  // Check if page exists
  pageExists?: (slug: string) => boolean
}

export class WikiProcessor {
  private options: Required<WikiProcessorOptions>
  private backlinks: Map<string, BacklinkReference[]> = new Map()
  private wikiLinks: Map<string, WikiLink[]> = new Map()

  constructor(options: WikiProcessorOptions = {}) {
    this.options = {
      pageResolver: options.pageResolver || (title => [this.titleToSlug(title)]),
      hrefTemplate: options.hrefTemplate || (slug => `/docs/${slug}`),
      pageExists: options.pageExists || (() => true),
    }
  }

  /**
   * Process all documents to build cross-reference index
   */
  processDocuments(docs: Doc[]): void {
    // Clear existing data
    this.backlinks.clear()
    this.wikiLinks.clear()

    // First pass: extract all wiki links
    for (const doc of docs) {
      const links = this.extractWikiLinks(doc.content)
      this.wikiLinks.set(doc.slug, links)

      // Record backlinks
      for (const link of links) {
        const targetSlug = this.titleToSlug(link.to)
        if (!this.backlinks.has(targetSlug)) {
          this.backlinks.set(targetSlug, [])
        }

        // Extract context around the link
        const context = this.extractContext(doc.content, link.text)

        this.backlinks.get(targetSlug)!.push({
          fromSlug: doc.slug,
          fromTitle: doc.title,
          context,
        })
      }
    }
  }

  /**
   * Extract wiki links from content
   */
  extractWikiLinks(content: string): WikiLink[] {
    const links: WikiLink[] = []
    const wikiLinkRegex = /\[\[([^\]|]+)(?:\|([^\]]+))?\]\]/g

    let match
    while ((match = wikiLinkRegex.exec(content)) !== null) {
      const target = match[1]?.trim() || ''
      const text = match[2]?.trim() || target
      const targetSlug = this.titleToSlug(target)

      links.push({
        from: '', // Will be set by caller
        to: target,
        text,
        exists: this.options.pageExists(targetSlug),
      })
    }

    return links
  }

  /**
   * Convert wiki links to markdown links
   */
  processWikiLinks(content: string): string {
    return content.replace(
      /\[\[([^\]|]+)(?:\|([^\]]+))?\]\]/g,
      (_, target: string, text?: string) => {
        const displayText = text || target
        const targetSlug = this.titleToSlug(target.trim())
        const exists = this.options.pageExists(targetSlug)
        const href = this.options.hrefTemplate(targetSlug)

        // Add CSS class to indicate if link exists
        const className = exists ? 'wiki-link' : 'wiki-link wiki-link-new'

        return `<a href="${href}" class="${className}">${displayText}</a>`
      }
    )
  }

  /**
   * Get backlinks for a document
   */
  getBacklinks(slug: string): BacklinkReference[] {
    return this.backlinks.get(slug) || []
  }

  /**
   * Get outgoing links from a document
   */
  getOutgoingLinks(slug: string): WikiLink[] {
    return this.wikiLinks.get(slug) || []
  }

  /**
   * Build graph data for visualization
   */
  buildGraphData(docs: Doc[]): {
    nodes: Array<{ id: string; label: string; group: string }>
    links: Array<{ source: string; target: string; type: string }>
  } {
    const nodes = docs.map(doc => ({
      id: doc.slug,
      label: doc.title,
      group: this.getDocumentGroup(doc),
    }))

    const links: Array<{ source: string; target: string; type: string }> = []

    for (const [fromSlug, wikiLinks] of this.wikiLinks) {
      for (const link of wikiLinks) {
        const targetSlug = this.titleToSlug(link.to)
        links.push({
          source: fromSlug,
          target: targetSlug,
          type: link.exists ? 'existing' : 'new',
        })
      }
    }

    return { nodes, links }
  }

  /**
   * Helper: Convert title to slug
   */
  private titleToSlug(title: string): string {
    return title
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, '-')
      .replace(/^-+|-+$/g, '')
  }

  /**
   * Helper: Extract context around a link
   */
  private extractContext(content: string, linkText: string, contextLength = 100): string {
    const index = content.indexOf(linkText)
    if (index === -1) return ''

    const start = Math.max(0, index - contextLength)
    const end = Math.min(content.length, index + linkText.length + contextLength)

    let context = content.slice(start, end)

    // Add ellipsis if truncated
    if (start > 0) context = '...' + context
    if (end < content.length) context = context + '...'

    return context
  }

  /**
   * Helper: Determine document group for visualization
   */
  private getDocumentGroup(doc: Doc): string {
    // Group by top-level directory
    const parts = doc.slug.split('/')
    if (parts.length > 1) {
      return parts[0] || 'root'
    }
    return 'root'
  }
}
