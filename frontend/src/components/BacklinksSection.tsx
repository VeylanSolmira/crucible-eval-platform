'use client'

import React from 'react'
import Link from 'next/link'
import type { BacklinkReference } from '@/lib/wiki/wiki-processor'

interface BacklinksSectionProps {
  backlinks: BacklinkReference[]
}

export function BacklinksSection({ backlinks }: BacklinksSectionProps) {
  if (!backlinks || backlinks.length === 0) {
    return null
  }

  return (
    <div className="mt-12 pt-8 border-t border-gray-200">
      <h2 className="text-xl font-semibold text-gray-900 mb-4">
        Referenced by
      </h2>
      <div className="space-y-3">
        {backlinks.map((backlink, index) => (
          <div
            key={`${backlink.fromSlug}-${index}`}
            className="p-4 bg-gray-50 rounded-lg hover:bg-gray-100 transition-colors"
          >
            <Link
              href={`/docs/${backlink.fromSlug}`}
              className="font-medium text-blue-600 hover:text-blue-700"
            >
              {backlink.fromTitle}
            </Link>
            {backlink.context && (
              <p className="mt-2 text-sm text-gray-600 italic">
                {backlink.context}
              </p>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}