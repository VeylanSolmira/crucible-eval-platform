/**
 * Automatic topic detection and wiki link suggestion system
 */

import type { Doc } from '../docs'

// Tier 1: Always auto-link these terms
const ALWAYS_LINK = new Set([
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
])

// Tier 2: Context-dependent linking
const CONTEXT_LINK = new Set([
  'Evaluation',
  'Evaluator',
  'Executor Service',
  'Monitoring Service',
  'Storage Service',
  'Microservices',
  'Security',
  'Threat Model',
  'Adversarial Testing',
  'Redis',
  'Python',
  'React',
  'Terraform',
  'OpenTofu'
])

// Canonical mappings for variations
const CANONICAL_FORMS: Record<string, string> = {
  'k8s': 'Kubernetes',
  'K8S': 'Kubernetes',
  'container isolation': 'Container Isolation',
  'Container isolation': 'Container Isolation',
  'threat model': 'Threat Model',
  'ai safety': 'AI Safety',
  'AI Safety': 'AI Safety',
  'Gvisor': 'gVisor',
  'GVISOR': 'gVisor'
}

export interface TopicDetectionOptions {
  enableAutoLink: boolean
  skipCodeBlocks: boolean
  skipUrls: boolean
  skipExistingLinks: boolean
  maxLinksPerTerm: number
  caseInsensitive: boolean
}

export interface DetectedTopic {
  term: string
  canonical: string
  positions: Array<{ start: number; end: number }>
  confidence: 'high' | 'medium' | 'low'
  autoLinkable: boolean
}

export class TopicDetector {
  private options: TopicDetectionOptions
  private existingDocs: Map<string, Doc>
  
  constructor(
    docs: Doc[],
    options: Partial<TopicDetectionOptions> = {}
  ) {
    this.options = {
      enableAutoLink: true,
      skipCodeBlocks: true,
      skipUrls: true,
      skipExistingLinks: true,
      maxLinksPerTerm: 3,
      caseInsensitive: false,
      ...options
    }
    
    // Build index of existing documents
    this.existingDocs = new Map()
    docs.forEach(doc => {
      this.existingDocs.set(doc.title.toLowerCase(), doc)
      this.existingDocs.set(doc.slug.toLowerCase(), doc)
    })
  }
  
  /**
   * Detect topics in content and suggest wiki links
   */
  detectTopics(content: string): DetectedTopic[] {
    const topics: DetectedTopic[] = []
    const processedTerms = new Map<string, number>()
    
    // Remove code blocks temporarily
    const codeBlocks: string[] = []
    let processedContent = content
    if (this.options.skipCodeBlocks) {
      processedContent = content.replace(/```[\s\S]*?```/g, (match) => {
        codeBlocks.push(match)
        return `__CODE_BLOCK_${codeBlocks.length - 1}__`
      })
    }
    
    // Skip existing wiki links
    if (this.options.skipExistingLinks) {
      processedContent = processedContent.replace(/\[\[[\s\S]*?\]\]/g, '__WIKI_LINK__')
    }
    
    // Detect Tier 1 topics (always link)
    ALWAYS_LINK.forEach(term => {
      const detections = this.findTerm(processedContent, term, 'high', true)
      topics.push(...detections)
    })
    
    // Detect Tier 2 topics (context-dependent)
    CONTEXT_LINK.forEach(term => {
      const detections = this.findTerm(processedContent, term, 'medium', true)
      topics.push(...detections)
    })
    
    // Detect document titles as topics
    this.existingDocs.forEach((doc) => {
      if (!ALWAYS_LINK.has(doc.title) && !CONTEXT_LINK.has(doc.title)) {
        const detections = this.findTerm(processedContent, doc.title, 'low', false)
        topics.push(...detections)
      }
    })
    
    // Apply max links per term limit
    const filteredTopics: DetectedTopic[] = []
    topics.forEach(topic => {
      const count = processedTerms.get(topic.canonical) || 0
      if (count < this.options.maxLinksPerTerm) {
        filteredTopics.push(topic)
        processedTerms.set(topic.canonical, count + 1)
      }
    })
    
    return filteredTopics
  }
  
  /**
   * Apply auto-linking to content
   */
  autoLink(content: string): string {
    if (!this.options.enableAutoLink) return content
    
    const topics = this.detectTopics(content)
    let result = content
    
    // Sort by position (reverse) to maintain correct offsets
    topics.sort((a, b) => {
      const bPos = b.positions[0]
      const aPos = a.positions[0]
      if (!bPos || !aPos) return 0
      return bPos.start - aPos.start
    })
    
    // Apply wiki links
    topics.forEach(topic => {
      if (topic.autoLinkable && topic.positions.length > 0) {
        const pos = topic.positions[0]
        if (pos) {
          result = 
            result.slice(0, pos.start) + 
            `[[${topic.canonical}]]` + 
            result.slice(pos.end)
        }
      }
    })
    
    return result
  }
  
  /**
   * Get suggestions for manual linking
   */
  getSuggestions(content: string): Array<{
    term: string
    canonical: string
    reason: string
    confidence: string
  }> {
    const topics = this.detectTopics(content)
    
    return topics
      .filter(t => !t.autoLinkable)
      .map(topic => ({
        term: topic.term,
        canonical: topic.canonical,
        reason: this.getSuggestionReason(topic),
        confidence: topic.confidence
      }))
  }
  
  private findTerm(
    content: string, 
    term: string, 
    confidence: 'high' | 'medium' | 'low',
    autoLinkable: boolean
  ): DetectedTopic[] {
    const topics: DetectedTopic[] = []
    const canonical = CANONICAL_FORMS[term] || term
    
    // Build regex pattern
    const pattern = this.options.caseInsensitive
      ? new RegExp(`\\b(${this.escapeRegex(term)})\\b`, 'gi')
      : new RegExp(`\\b(${this.escapeRegex(term)})\\b`, 'g')
    
    let match
    const positions: Array<{ start: number; end: number }> = []
    
    while ((match = pattern.exec(content)) !== null) {
      // Skip if inside a code block placeholder
      if (content.slice(match.index - 15, match.index).includes('__CODE_BLOCK_')) {
        continue
      }
      
      // Skip if inside a URL
      if (this.options.skipUrls && this.isInsideUrl(content, match.index)) {
        continue
      }
      
      positions.push({
        start: match.index,
        end: match.index + match[0].length
      })
    }
    
    if (positions.length > 0) {
      topics.push({
        term,
        canonical,
        positions,
        confidence,
        autoLinkable
      })
    }
    
    return topics
  }
  
  private isInsideUrl(content: string, position: number): boolean {
    // Simple heuristic: check if position is between http(s):// and whitespace
    const before = content.slice(Math.max(0, position - 50), position)
    const after = content.slice(position, position + 50)
    
    return (
      (before.includes('http://') || before.includes('https://')) &&
      !after.match(/\s/)
    )
  }
  
  private escapeRegex(str: string): string {
    return str.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
  }
  
  private getSuggestionReason(topic: DetectedTopic): string {
    if (topic.confidence === 'low') {
      return `Found document titled "${topic.canonical}"`
    }
    if (topic.confidence === 'medium') {
      return 'Common platform term that may benefit from linking'
    }
    return 'High-priority term'
  }
}

/**
 * React hook for topic detection
 */
export function useTopicDetection(
  content: string,
  docs: Doc[],
  options?: Partial<TopicDetectionOptions>
) {
  const detector = new TopicDetector(docs, options)
  
  return {
    topics: detector.detectTopics(content),
    autoLinkedContent: detector.autoLink(content),
    suggestions: detector.getSuggestions(content)
  }
}