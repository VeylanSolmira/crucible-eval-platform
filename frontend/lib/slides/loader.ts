import fs from 'fs/promises'
import path from 'path'
import matter from 'gray-matter'

export interface SlideMetadata {
  id: string
  title: string
  file: string
  duration: number
  tags: string[]
  description?: string
}

export interface Slide extends SlideMetadata {
  content: string
  sections: string[]
}

export interface SlidesIndex {
  title: string
  description: string
  author: string
  date: string
  theme: string
  slides: SlideMetadata[]
}

const SLIDES_DIR = path.join(process.cwd(), 'content', 'slides')

/**
 * Load the slides index from index.json
 */
export async function loadSlidesIndex(): Promise<SlidesIndex> {
  const indexPath = path.join(SLIDES_DIR, 'index.json')
  const content = await fs.readFile(indexPath, 'utf-8')
  return JSON.parse(content) as SlidesIndex
}

/**
 * Load a single slide by ID
 */
export async function loadSlide(id: string): Promise<Slide | null> {
  try {
    // First load the index to get metadata
    const index = await loadSlidesIndex()
    const metadata = index.slides.find(s => s.id === id)

    if (!metadata) {
      console.error(`Slide ${id} not found in index`)
      return null
    }

    // Load the content file
    const filePath = path.join(SLIDES_DIR, metadata.file)
    const content = await fs.readFile(filePath, 'utf-8')

    // Parse frontmatter if present, otherwise use raw content
    const { data, content: markdown } = matter(content)

    // Split content into sections (separated by ---)
    const sections = markdown
      .split(/\n---\n/)
      .map(s => s.trim())
      .filter(Boolean)

    // Merge metadata from index with frontmatter data
    const slide: Slide = {
      id: metadata.id,
      title: (data.title as string) || metadata.title,
      file: metadata.file,
      duration: (data.duration as number) || metadata.duration,
      tags: (data.tags as string[]) || metadata.tags,
      content: markdown,
      sections,
    }

    // Only add description if it exists
    const description = (data.description as string) || metadata.description
    if (description) {
      slide.description = description
    }

    return slide
  } catch (error) {
    console.error(`Error loading slide ${id}:`, error)
    return null
  }
}

/**
 * Load all slides
 */
export async function loadAllSlides(): Promise<Slide[]> {
  const index = await loadSlidesIndex()
  const slides = await Promise.all(index.slides.map(metadata => loadSlide(metadata.id)))

  // Sort slides by their position in the index
  const slideOrder = index.slides.map(s => s.id)
  return slides
    .filter((slide): slide is Slide => slide !== null)
    .sort((a, b) => slideOrder.indexOf(a.id) - slideOrder.indexOf(b.id))
}

/**
 * Get slides by tag
 */
export async function getSlidesByTag(tag: string): Promise<Slide[]> {
  const slides = await loadAllSlides()
  return slides.filter(slide => slide.tags.includes(tag))
}

/**
 * Search slides by content
 */
export async function searchSlides(query: string): Promise<Slide[]> {
  const slides = await loadAllSlides()
  const lowerQuery = query.toLowerCase()

  return slides.filter(
    slide =>
      slide.title.toLowerCase().includes(lowerQuery) ||
      slide.content.toLowerCase().includes(lowerQuery) ||
      slide.tags.some(tag => tag.toLowerCase().includes(lowerQuery))
  )
}
