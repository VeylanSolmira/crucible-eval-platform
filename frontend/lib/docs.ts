import fs from 'fs'
import path from 'path'
import matter from 'gray-matter'
import { globSync } from 'glob'

// Frontmatter type
interface Frontmatter {
  title?: string;
  description?: string;
  order?: number;
  [key: string]: unknown;
}

// Preprocessed docs cache
interface ProcessedDoc {
  frontmatter: Frontmatter;
  content: string;
  hash: string;
  path: string;
}

let docsCache: Record<string, ProcessedDoc> | null = null;

// Load preprocessed docs if available
function loadDocsCache(): Record<string, ProcessedDoc> {
  if (docsCache) return docsCache;
  
  const cacheFile = path.join(process.cwd(), '.docs-cache', 'processed-docs.json');
  
  try {
    if (fs.existsSync(cacheFile)) {
      console.log('[Docs] Using preprocessed documentation cache');
      docsCache = JSON.parse(fs.readFileSync(cacheFile, 'utf8'));
      return docsCache!;
    }
  } catch (error) {
    console.warn('[Docs] Failed to load preprocessed cache, falling back to runtime processing');
  }
  
  // Fallback to empty cache
  docsCache = {};
  return docsCache;
}

export interface DocMeta {
  title: string
  description?: string
  order?: number
  lastModified?: string
  readingTime?: number
  prev?: {
    title: string
    slug: string
  }
  next?: {
    title: string
    slug: string
  }
}

export interface Doc extends DocMeta {
  slug: string
  content: string
}

// Documentation source configuration
interface DocSource {
  urlPrefix: string
  fsPath: string
  label: string
  include?: string[]
  exclude?: string[]
}

// Documentation sources - maps URL paths to file system paths
const DOC_SOURCES: DocSource[] = [
  {
    urlPrefix: '',
    fsPath: 'docs',
    label: 'Platform Docs',
    include: ['**/*.md'],
    exclude: ['**/README.md', '**/node_modules/**']
  },
  {
    urlPrefix: 'frontend',
    fsPath: 'frontend/docs',
    label: 'Frontend Docs',
    include: ['**/*.md'],
    exclude: []
  },
  {
    urlPrefix: 'api',
    fsPath: 'docs/api',
    label: 'API Docs',
    include: ['**/*.md'],
    exclude: []
  },
  // Add more sources as needed
  {
    urlPrefix: 'infrastructure',
    fsPath: 'infrastructure',
    label: 'Infrastructure',
    include: ['**/*.md'],
    exclude: ['**/node_modules/**', '**/.terraform/**']
  }
]

// Get the project root directory
const ROOT_DIR = process.cwd()

// Convert file path to URL slug
function filePathToSlug(filePath: string, source: typeof DOC_SOURCES[0]): string {
  // Remove the source path prefix and .md extension
  let slug = filePath
    .replace(source.fsPath + '/', '')
    .replace(/\.md$/, '')
  
  // Add URL prefix if needed
  if (source.urlPrefix) {
    slug = `${source.urlPrefix}/${slug}`
  }
  
  return slug
}

// Convert URL slug to file path
function slugToFilePath(slug: string[]): string | null {
  const joinedSlug = slug.join('/')
  
  // Try each source to find the file
  for (const source of DOC_SOURCES) {
    let testSlug = joinedSlug
    
    // Remove URL prefix if it matches
    if (source.urlPrefix && joinedSlug.startsWith(source.urlPrefix + '/')) {
      testSlug = joinedSlug.slice(source.urlPrefix.length + 1)
    } else if (source.urlPrefix) {
      // This source doesn't match
      continue
    }
    
    const filePath = path.join(ROOT_DIR, source.fsPath, `${testSlug}.md`)
    
    if (fs.existsSync(filePath)) {
      return filePath
    }
  }
  
  return null
}

// Get all documentation file paths
export async function getDocPaths(): Promise<string[]> {
  const allPaths: string[] = []
  
  for (const source of DOC_SOURCES) {
    const pattern = path.join(ROOT_DIR, source.fsPath, '**/*.md')
    const files = globSync(pattern)
    
    // Convert file paths to URL slugs
    const slugs = files.map((file: string) => {
      const relativePath = path.relative(path.join(ROOT_DIR, source.fsPath), file)
      return filePathToSlug(relativePath, source)
    })
    
    allPaths.push(...slugs)
  }
  
  return allPaths
}

// Get all docs with metadata
export async function getAllDocs(): Promise<Doc[]> {
  const paths = await getDocPaths()
  const docs: Doc[] = []
  
  for (const docPath of paths) {
    const doc = await getDocBySlug(docPath.split('/'))
    if (doc) {
      docs.push(doc)
    }
  }
  
  return docs.sort((a, b) => {
    // Sort by order if specified, otherwise alphabetically
    if (a.order !== undefined && b.order !== undefined) {
      return a.order - b.order
    }
    return a.title.localeCompare(b.title)
  })
}

// Get a single doc by slug
export async function getDocBySlug(slug: string[]): Promise<Doc | null> {
  const filePath = slugToFilePath(slug)
  
  if (!filePath) {
    return null
  }
  
  // Check cache first
  const cache = loadDocsCache();
  const relativePath = path.relative(path.join(process.cwd(), 'docs'), filePath);
  const cachedDoc = cache[relativePath];
  
  let data: Frontmatter;
  let content: string;
  let stats: fs.Stats;
  
  if (cachedDoc) {
    // Use cached content
    data = cachedDoc.frontmatter;
    content = cachedDoc.content;
    // Still need stats for last modified (unless we cache that too)
    if (fs.existsSync(filePath)) {
      stats = fs.statSync(filePath);
    } else {
      return null;
    }
  } else {
    // Fallback to reading from filesystem
    if (!fs.existsSync(filePath)) {
      return null;
    }
    
    const fileContent = fs.readFileSync(filePath, 'utf-8')
    const parsed = matter(fileContent)
    data = parsed.data
    content = parsed.content
    stats = fs.statSync(filePath)
  }
  
  // Calculate reading time (rough estimate: 200 words per minute)
  const wordCount = content.split(/\s+/).length
  const readingTime = Math.ceil(wordCount / 200)
  
  // Extract title from frontmatter or first H1
  let title: string
  if (data.title) {
    title = data.title as string
  } else {
    const h1Match = content.match(/^#\s+(.+)$/m)
    if (h1Match && h1Match[1]) {
      title = h1Match[1]
    } else {
      const lastSegment = slug[slug.length - 1]
      title = lastSegment ? lastSegment.replace(/-/g, ' ') : 'Untitled'
    }
  }
  
  return {
    slug: slug.join('/'),
    title,
    ...(data.description && { description: data.description as string }),
    ...(data.order !== undefined && { order: data.order as number }),
    content,
    lastModified: stats.mtime.toISOString(),
    readingTime,
    // Navigation links will be added by the page component
  }
}

// Build navigation structure from all docs
export async function buildNavigation() {
  const docs = await getAllDocs()
  
  interface NavigationNode {
    _type?: 'folder' | 'doc';
    _children?: Record<string, NavigationNode>;
    title?: string;
    slug?: string;
    order?: number;
  }
  
  const navigation: Record<string, NavigationNode> = {}
  
  for (const doc of docs) {
    const parts = doc.slug.split('/')
    let current = navigation
    
    // Build nested structure
    for (let i = 0; i < parts.length - 1; i++) {
      const part = parts[i]
      if (!part) continue
      
      if (!current[part]) {
        current[part] = {
          _type: 'folder',
          _children: {}
        }
      }
      current = current[part]._children || {}
    }
    
    // Add the document
    const fileName = parts[parts.length - 1]
    if (!fileName) continue
    
    current[fileName] = {
      _type: 'doc',
      title: doc.title,
      slug: doc.slug,
      ...(doc.order !== undefined && { order: doc.order })
    }
  }
  
  return navigation
}