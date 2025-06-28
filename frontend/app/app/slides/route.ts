import { NextRequest, NextResponse } from 'next/server'
import { saveSlide, deleteSlide, createSlide } from '@/lib/slides/server-actions'
import { Slide } from '@/lib/slides/loader'

export async function POST(request: NextRequest) {
  try {
    const body = await request.json()
    
    if (body.action === 'create') {
      const { title, tags } = body
      const newSlide = await createSlide(title, tags)
      return NextResponse.json(newSlide)
    } else if (body.action === 'save') {
      const slide: Slide = body.slide
      await saveSlide(slide)
      return NextResponse.json({ success: true })
    } else {
      return NextResponse.json(
        { error: 'Invalid action' },
        { status: 400 }
      )
    }
  } catch (error) {
    console.error('Error in slides API:', error)
    return NextResponse.json(
      { error: error instanceof Error ? error.message : 'Internal server error' },
      { status: 500 }
    )
  }
}

export async function DELETE(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url)
    const slideId = searchParams.get('id')
    
    if (!slideId) {
      return NextResponse.json(
        { error: 'Slide ID is required' },
        { status: 400 }
      )
    }
    
    await deleteSlide(slideId)
    return NextResponse.json({ success: true })
  } catch (error) {
    console.error('Error deleting slide:', error)
    return NextResponse.json(
      { error: error instanceof Error ? error.message : 'Internal server error' },
      { status: 500 }
    )
  }
}