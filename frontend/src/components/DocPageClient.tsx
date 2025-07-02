'use client'

import React from 'react'
import { MarkdownRenderer } from './MarkdownRenderer'
import { BacklinksSection } from './BacklinksSection'
import type { BacklinkReference } from '@/lib/wiki/wiki-processor'

interface DocPageClientProps {
  content: string
  slug: string
  backlinks?: BacklinkReference[]
}

export function DocPageClient({ content, backlinks = [] }: DocPageClientProps) {
  return (
    <>
      <div className="prose prose-gray max-w-none">
        <MarkdownRenderer content={content} />
      </div>

      <BacklinksSection backlinks={backlinks} />
    </>
  )
}
