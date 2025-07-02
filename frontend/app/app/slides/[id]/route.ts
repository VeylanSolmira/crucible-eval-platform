import { type NextRequest, NextResponse } from 'next/server'
import { updateSlideContent, deleteSlide } from '@/lib/slides/server-actions'

interface UpdateSlideBody {
  content: string
}

export async function PUT(request: NextRequest, { params }: { params: Promise<{ id: string }> }) {
  try {
    const { id } = await params
    const body = (await request.json()) as UpdateSlideBody
    const { content } = body

    if (!content) {
      return NextResponse.json({ error: 'Content is required' }, { status: 400 })
    }

    await updateSlideContent(id, content)

    return NextResponse.json({ success: true })
  } catch (error) {
    console.error('Error saving slide:', error)
    return NextResponse.json({ error: 'Failed to save slide' }, { status: 500 })
  }
}

export async function DELETE(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const { id } = await params
    // Log the deletion request with user agent for audit
    const userAgent = request.headers.get('user-agent') || 'unknown'
    console.info(`DELETE request for slide: ${id} from ${userAgent}`)

    await deleteSlide(id)

    return NextResponse.json({ success: true })
  } catch (error) {
    console.error('Error deleting slide:', error)
    return NextResponse.json({ error: 'Failed to delete slide' }, { status: 500 })
  }
}
