'use server'

import fs from 'fs/promises'
import path from 'path'
import { Slide, SlideMetadata, SlidesIndex } from './loader'

const SLIDES_DIR = path.join(process.cwd(), 'content', 'slides')

/**
 * Save a slide to the file system
 */
export async function saveSlide(slide: Slide): Promise<void> {
  const filePath = path.join(SLIDES_DIR, `${slide.id}.md`)
  
  // Create frontmatter
  const frontmatter = `---
title: "${slide.title}"
duration: ${slide.duration}
tags: [${slide.tags.map(t => `"${t}"`).join(', ')}]${
    slide.description ? `\ndescription: "${slide.description}"` : ''
  }
---`
  
  // Combine frontmatter and content
  const fullContent = `${frontmatter}\n\n${slide.content}`
  
  // Write to file
  await fs.writeFile(filePath, fullContent, 'utf-8')
  
  // Update index.json
  await updateSlidesIndex(slide)
}

/**
 * Update slide content by ID
 */
export async function updateSlideContent(slideId: string, content: string): Promise<void> {
  const filePath = path.join(SLIDES_DIR, `${slideId}.md`)
  
  // Read existing file to preserve frontmatter
  const existingContent = await fs.readFile(filePath, 'utf-8')
  const frontmatterMatch = existingContent.match(/^---\n([\s\S]*?)\n---/)
  
  if (!frontmatterMatch) {
    throw new Error('No frontmatter found in slide')
  }
  
  // Combine existing frontmatter with new content
  const fullContent = `---\n${frontmatterMatch[1]}\n---\n\n${content}`
  
  // Write to file
  await fs.writeFile(filePath, fullContent, 'utf-8')
}

/**
 * Delete a slide from the file system
 */
export async function deleteSlide(slideId: string): Promise<void> {
  const filePath = path.join(SLIDES_DIR, `${slideId}.md`)
  
  try {
    // Delete the file
    await fs.unlink(filePath)
    
    // Update index.json
    await removeFromSlidesIndex(slideId)
  } catch (error) {
    console.error(`Error deleting slide ${slideId}:`, error)
    throw error
  }
}

/**
 * Create a new slide
 */
export async function createSlide(title: string, tags: string[] = []): Promise<Slide> {
  // Get current slides to determine order
  const indexPath = path.join(SLIDES_DIR, 'index.json')
  const indexContent = await fs.readFile(indexPath, 'utf-8')
  const index: SlidesIndex = JSON.parse(indexContent)
  
  // Generate ID
  const id = title.toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-|-$/g, '')
  
  // Check if ID already exists
  let uniqueId = id
  let counter = 1
  while (index.slides.some(s => s.id === uniqueId)) {
    uniqueId = `${id}-${counter}`
    counter++
  }
  
  const newSlide: Slide = {
    id: uniqueId,
    title,
    file: `${uniqueId}.md`,
    duration: 2,
    tags,
    content: `# ${title}\n\nAdd your content here...`,
    sections: [`# ${title}\n\nAdd your content here...`]
  }
  
  await saveSlide(newSlide)
  return newSlide
}

/**
 * Update the slides index
 */
async function updateSlidesIndex(slide: Slide): Promise<void> {
  const indexPath = path.join(SLIDES_DIR, 'index.json')
  const indexContent = await fs.readFile(indexPath, 'utf-8')
  const index: SlidesIndex = JSON.parse(indexContent)
  
  // Update or add slide metadata
  const existingIndex = index.slides.findIndex(s => s.id === slide.id)
  const metadata: SlideMetadata = {
    id: slide.id,
    title: slide.title,
    file: slide.file,
    duration: slide.duration,
    tags: slide.tags
  }
  
  // Only add description if it exists
  if (slide.description) {
    metadata.description = slide.description
  }
  
  if (existingIndex >= 0) {
    index.slides[existingIndex] = metadata
  } else {
    index.slides.push(metadata)
  }
  
  // Keep original order unless explicitly changed
  // index.slides array order determines display order
  
  // Update last updated date
  index.date = new Date().toISOString().split('T')[0]!
  
  // Write back to file
  await fs.writeFile(indexPath, JSON.stringify(index, null, 2), 'utf-8')
}

/**
 * Remove a slide from the index
 */
async function removeFromSlidesIndex(slideId: string): Promise<void> {
  const indexPath = path.join(SLIDES_DIR, 'index.json')
  const indexContent = await fs.readFile(indexPath, 'utf-8')
  const index: SlidesIndex = JSON.parse(indexContent)
  
  // Remove slide
  index.slides = index.slides.filter(s => s.id !== slideId)
  
  // Array order determines display order
  // No need to update order property
  
  // Update last updated date
  index.date = new Date().toISOString().split('T')[0]!
  
  // Write back to file
  await fs.writeFile(indexPath, JSON.stringify(index, null, 2), 'utf-8')
}