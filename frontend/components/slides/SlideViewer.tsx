'use client'

import { useEffect, useRef, useState } from 'react'
import Reveal from 'reveal.js'
import Markdown from 'reveal.js/plugin/markdown/markdown'
import Highlight from 'reveal.js/plugin/highlight/highlight'
import Notes from 'reveal.js/plugin/notes/notes'
import 'reveal.js/dist/reveal.css'
import 'reveal.js/dist/theme/black.css'
import 'reveal.js/plugin/highlight/monokai.css'
import type { Slide } from '@/lib/slides/loader'

interface SlideViewerProps {
  slides: Slide[]
  theme?:
    | 'black'
    | 'white'
    | 'league'
    | 'beige'
    | 'sky'
    | 'night'
    | 'serif'
    | 'simple'
    | 'solarized'
  transition?: 'none' | 'fade' | 'slide' | 'convex' | 'concave' | 'zoom'
}

export function SlideViewer({ slides, theme = 'black', transition = 'slide' }: SlideViewerProps) {
  const deckRef = useRef<HTMLDivElement>(null)
  const revealRef = useRef<Reveal.Api | null>(null)
  const [currentSlideIndex, setCurrentSlideIndex] = useState(0)

  useEffect(() => {
    if (!deckRef.current || slides.length === 0) return

    // Debug: Log what we're rendering
    console.info('Slides:', slides)
    slides.forEach((slide, i) => {
      console.info(`Slide ${i} sections:`, slide.sections)
    })

    // Initialize Reveal.js
    const deck = new Reveal(deckRef.current, {
      plugins: [Markdown, Highlight, Notes],
      hash: false,
      history: false,
      controls: true,
      progress: true,
      center: true,
      transition,
      transitionSpeed: 'default',
      backgroundTransition: 'fade',
      embedded: true, // Changed to embedded mode for better container handling
      width: 1024,
      height: 768,
      margin: 0.04,
      minScale: 0.2,
      maxScale: 2.0,
      navigationMode: 'default', // Allows both horizontal and vertical navigation
    })

    void deck.initialize().then(() => {
      revealRef.current = deck

      // Listen for slide changes
      deck.on('slidechanged', (event: { indexh: number }) => {
        setCurrentSlideIndex(event.indexh)
      })
    })

    return () => {
      if (revealRef.current) {
        revealRef.current.destroy()
      }
    }
  }, [slides, transition])

  // Dynamically import theme CSS
  useEffect(() => {
    import(`reveal.js/dist/theme/${theme}.css`).catch(err =>
      console.error(`Failed to load theme ${theme}:`, err)
    )
  }, [theme])

  return (
    <div className="slide-viewer h-screen w-full relative overflow-hidden">
      <div className="reveal" ref={deckRef} style={{ height: '100%' }}>
        <div className="slides">
          {slides.map(slide => (
            <section key={slide.id}>
              {slide.sections.map((section, index) => (
                <section
                  key={`${slide.id}-${index}`}
                  data-markdown=""
                  data-separator="^\n---\n"
                  data-separator-vertical="^\n--\n"
                  data-separator-notes="^Note:"
                >
                  <textarea data-template style={{ display: 'none' }}>
                    {section}
                  </textarea>
                </section>
              ))}
            </section>
          ))}
        </div>
      </div>

      {/* Slide counter */}
      <div className="absolute bottom-4 right-4 bg-black/50 text-white px-3 py-1 rounded-full text-sm">
        {currentSlideIndex + 1} / {slides.length}
      </div>
    </div>
  )
}
