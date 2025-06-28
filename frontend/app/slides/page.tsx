import { loadAllSlides } from '@/lib/slides/loader'
import SlidesPageClient from './SlidesPageClient'
import './slides.css'

export default async function SlidesPage() {
  const slides = await loadAllSlides()

  return (
    <div className="h-screen flex flex-col">
      <header className="bg-gray-900 text-white p-4">
        <h1 className="text-2xl font-bold">METR Platform Slides</h1>
      </header>
      <SlidesPageClient slides={slides} />
    </div>
  )
}