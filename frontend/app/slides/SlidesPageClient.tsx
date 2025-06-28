'use client'

import dynamic from 'next/dynamic'
import { Slide } from '@/lib/slides/loader'

// Dynamically import SlidesContainer to avoid SSR issues with reveal.js
const SlidesContainer = dynamic(() => import('./SlidesContainer'), {
  ssr: false,
  loading: () => (
    <div className="flex-1 flex items-center justify-center">
      <div className="text-center">
        <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-gray-900"></div>
        <p className="mt-2 text-gray-600">Loading slides...</p>
      </div>
    </div>
  )
})

interface SlidesPageClientProps {
  slides: Slide[]
}

export default function SlidesPageClient({ slides }: SlidesPageClientProps) {
  return <SlidesContainer initialSlides={slides} />
}