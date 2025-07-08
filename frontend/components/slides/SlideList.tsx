'use client'

import { useState } from 'react'
import type { Slide } from '@/lib/slides/loader'

interface SlideListProps {
  slides: Slide[]
  onSelectSlide: (slide: Slide) => void
  onEditSlide: (slide: Slide) => void
  onDeleteSlide?: (slideId: string) => void
  selectedSlideId?: string
}

export function SlideList({
  slides,
  onSelectSlide,
  onEditSlide,
  onDeleteSlide,
  selectedSlideId,
}: SlideListProps) {
  const [searchQuery, setSearchQuery] = useState('')
  const [selectedTag, setSelectedTag] = useState<string | null>(null)

  // Get all unique tags
  const allTags = Array.from(new Set(slides.flatMap(slide => slide.tags))).sort()

  // Filter slides based on search and tag
  const filteredSlides = slides.filter(slide => {
    const matchesSearch =
      searchQuery === '' ||
      slide.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
      slide.content.toLowerCase().includes(searchQuery.toLowerCase())

    const matchesTag = selectedTag === null || slide.tags.includes(selectedTag)

    return matchesSearch && matchesTag
  })

  return (
    <div className="slide-list h-full flex flex-col">
      {/* Search and filters */}
      <div className="p-4 border-b space-y-3">
        <input
          type="text"
          placeholder="Search slides..."
          value={searchQuery}
          onChange={e => setSearchQuery(e.target.value)}
          className="w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
        />

        {/* Tag filters */}
        {allTags.length > 0 && (
          <div className="flex flex-wrap gap-1 max-h-16 overflow-y-auto">
            <button
              onClick={() => setSelectedTag(null)}
              className={`px-2 py-0.5 rounded-full text-xs ${
                selectedTag === null
                  ? 'bg-blue-500 text-white'
                  : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
              }`}
            >
              All
            </button>
            {allTags.map(tag => (
              <button
                key={tag}
                onClick={() => setSelectedTag(tag)}
                className={`px-2 py-0.5 rounded-full text-xs ${
                  selectedTag === tag
                    ? 'bg-blue-500 text-white'
                    : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
                }`}
              >
                {tag}
              </button>
            ))}
          </div>
        )}
      </div>

      {/* Slide list */}
      <div className="flex-1 overflow-y-auto">
        {filteredSlides.length === 0 ? (
          <div className="p-8 text-center text-gray-500">No slides found</div>
        ) : (
          <div className="divide-y">
            {filteredSlides.map((slide, index) => (
              <div
                key={slide.id}
                className={`p-4 hover:bg-gray-50 cursor-pointer transition-colors ${
                  selectedSlideId === slide.id ? 'bg-blue-50' : ''
                }`}
                onClick={() => onSelectSlide(slide)}
              >
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <h3 className="font-semibold text-gray-900">
                      {index + 1}. {slide.title}
                    </h3>
                    {slide.description && (
                      <p className="text-sm text-gray-600 mt-1">{slide.description}</p>
                    )}
                    <div className="flex gap-2 mt-2">
                      {slide.tags.map(tag => (
                        <span
                          key={tag}
                          className="px-2 py-1 bg-gray-100 text-gray-700 text-xs rounded"
                        >
                          {tag}
                        </span>
                      ))}
                    </div>
                  </div>

                  <div className="flex gap-2 ml-4">
                    <button
                      onClick={e => {
                        e.stopPropagation()
                        onEditSlide(slide)
                      }}
                      className="px-3 py-1 text-sm bg-gray-200 text-gray-700 rounded hover:bg-gray-300"
                    >
                      Edit
                    </button>
                    {onDeleteSlide && (
                      <button
                        onClick={e => {
                          e.stopPropagation()
                          if (confirm(`Delete slide "${slide.title}"?`)) {
                            onDeleteSlide(slide.id)
                          }
                        }}
                        className="px-3 py-1 text-sm bg-red-500 text-white rounded hover:bg-red-600"
                      >
                        Delete
                      </button>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Stats */}
      <div className="p-4 border-t text-sm text-gray-600">
        Showing {filteredSlides.length} of {slides.length} slides
      </div>
    </div>
  )
}
