import { NextResponse } from 'next/server'
import { loadAllTemplates } from '@/lib/templates/loader'

export async function GET() {
  try {
    const templates = await loadAllTemplates()
    return NextResponse.json(templates)
  } catch (error) {
    console.error('Error loading templates:', error)
    return NextResponse.json(
      { error: 'Failed to load templates' },
      { status: 500 }
    )
  }
}