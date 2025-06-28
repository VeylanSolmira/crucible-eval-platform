'use client'

import { useState } from 'react'
import { Slide } from '@/lib/slides/loader'
import { SlideList } from '@/components/slides/SlideList'
import { SlideViewer } from '@/components/slides/SlideViewer'
import { SlideEditor } from '@/components/slides/SlideEditor'

interface SlidesContainerProps {
  initialSlides: Slide[]
}

type ViewMode = 'list' | 'presentation' | 'edit'

export default function SlidesContainer({ initialSlides }: SlidesContainerProps) {
  const [slides, setSlides] = useState<Slide[]>(initialSlides)
  const [selectedSlide, setSelectedSlide] = useState<Slide | null>(null)
  const [viewMode, setViewMode] = useState<ViewMode>('list')
  const [presentationSlides, setPresentationSlides] = useState<Slide[]>([])

  const handleSelectSlide = (slide: Slide) => {
    setSelectedSlide(slide)
    setPresentationSlides([slide])
  }

  const handleEditSlide = (slide: Slide) => {
    setSelectedSlide(slide)
    setViewMode('edit')
  }

  const handleSaveSlide = async (updatedSlide: Slide) => {
    try {
      const response = await fetch('/app/slides', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          action: 'save',
          slide: updatedSlide
        }),
      })
      
      if (!response.ok) {
        throw new Error('Failed to save slide')
      }
      
      // Update local state
      setSlides(slides.map(s => s.id === updatedSlide.id ? updatedSlide : s))
      setSelectedSlide(updatedSlide)
      setViewMode('list')
    } catch (error) {
      console.error('Error saving slide:', error)
      alert('Failed to save slide. Please try again.')
    }
  }

  const handleDeleteSlide = async (slideId: string) => {
    try {
      const response = await fetch(`/app/slides?id=${slideId}`, {
        method: 'DELETE',
      })
      
      if (!response.ok) {
        throw new Error('Failed to delete slide')
      }
      
      // Update local state
      setSlides(slides.filter(s => s.id !== slideId))
      if (selectedSlide?.id === slideId) {
        setSelectedSlide(null)
      }
    } catch (error) {
      console.error('Error deleting slide:', error)
      alert('Failed to delete slide. Please try again.')
    }
  }

  const handlePresentAll = () => {
    setPresentationSlides(slides)
    setViewMode('presentation')
  }

  const handlePresentFromCurrent = () => {
    if (selectedSlide) {
      const currentIndex = slides.findIndex(s => s.id === selectedSlide.id)
      setPresentationSlides(slides.slice(currentIndex))
      setViewMode('presentation')
    }
  }

  if (viewMode === 'presentation') {
    return (
      <div className="relative h-full">
        <SlideViewer slides={presentationSlides} />
        <button
          onClick={() => setViewMode('list')}
          className="absolute top-4 left-4 px-4 py-2 bg-black/50 text-white rounded hover:bg-black/70 z-10"
        >
          Exit Presentation
        </button>
      </div>
    )
  }

  if (viewMode === 'edit' && selectedSlide) {
    return (
      <SlideEditor
        slide={selectedSlide}
        onSave={handleSaveSlide}
        onCancel={() => setViewMode('list')}
      />
    )
  }

  return (
    <div className="flex-1 flex overflow-hidden">
      {/* Sidebar */}
      <div className="w-96 border-r bg-white">
        <SlideList
          slides={slides}
          onSelectSlide={handleSelectSlide}
          onEditSlide={handleEditSlide}
          onDeleteSlide={handleDeleteSlide}
          selectedSlideId={selectedSlide?.id || ''}
        />
      </div>

      {/* Main content */}
      <div className="flex-1 flex flex-col">
        {selectedSlide ? (
          <>
            {/* Toolbar */}
            <div className="p-4 border-b bg-gray-50 flex items-center justify-between">
              <h2 className="text-lg font-semibold">{selectedSlide.title}</h2>
              <div className="flex gap-2">
                <button
                  onClick={() => handlePresentFromCurrent()}
                  className="px-4 py-2 bg-green-500 text-white rounded hover:bg-green-600"
                >
                  Present from Here
                </button>
                <button
                  onClick={handlePresentAll}
                  className="px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600"
                >
                  Present All
                </button>
              </div>
            </div>

            {/* Preview */}
            <div className="flex-1 p-8 overflow-y-auto">
              <div className="prose prose-lg max-w-none">
                {selectedSlide.sections.map((section, index) => (
                  <div key={index} className="mb-12 pb-12 border-b last:border-0">
                    <div className="slide-section" dangerouslySetInnerHTML={{ 
                      __html: section.replace(/```(\w+)?\n([\s\S]*?)```/g, (_match, lang, code) => {
                        return `<pre><code class="language-${lang || 'plaintext'}">${code.trim()}</code></pre>`
                      })
                    }} />
                  </div>
                ))}
              </div>
            </div>
          </>
        ) : (
          <div className="flex-1 flex items-center justify-center text-gray-500">
            <div className="text-center">
              <p className="text-xl mb-4">Select a slide to preview</p>
              <button
                onClick={handlePresentAll}
                className="px-6 py-3 bg-blue-500 text-white rounded-lg hover:bg-blue-600"
              >
                Present All Slides
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}