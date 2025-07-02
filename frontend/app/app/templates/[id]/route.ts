import { type NextRequest, NextResponse } from 'next/server'
import { loadTemplate } from '@/lib/templates/loader'

export async function GET(request: NextRequest, { params }: { params: Promise<{ id: string }> }) {
  try {
    const { id } = await params

    // Log request for debugging
    console.info(`Template request: ${id} from ${request.headers.get('user-agent')}`)

    const template = await loadTemplate(id)

    if (!template) {
      return NextResponse.json({ error: 'Template not found' }, { status: 404 })
    }

    return NextResponse.json(template)
  } catch (error) {
    console.error('Error loading template:', error)
    return NextResponse.json({ error: 'Failed to load template' }, { status: 500 })
  }
}
