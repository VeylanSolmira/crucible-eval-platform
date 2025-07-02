import { notFound } from 'next/navigation'
import Link from 'next/link'
import { getDocBySlug } from '@/lib/docs'
import { DocPageClient } from '@/src/components/DocPageClient'
import { getBacklinksForDoc } from '@/lib/wiki/process-backlinks'
import type { Metadata } from 'next'

interface PageProps {
  params: Promise<{
    slug: string[]
  }>
}

export async function generateMetadata({ params }: PageProps): Promise<Metadata> {
  const { slug } = await params
  const doc = await getDocBySlug(slug)

  if (!doc) {
    return {
      title: 'Not Found - Crucible Docs',
    }
  }

  return {
    title: `${doc.title} - Crucible Docs`,
    description: doc.description || `Documentation for ${doc.title}`,
  }
}

export function generateStaticParams() {
  // Only pre-build essential docs during build time
  // Others will be built on-demand (ISR)
  const criticalDocs = ['quickstart', 'README', 'architecture/overview', 'getting-started']

  // Always only pre-build critical docs (both dev and prod)
  return criticalDocs.map(path => ({
    slug: path.split('/'),
  }))
}

export default async function DocPage({ params }: PageProps) {
  const { slug } = await params
  const doc = await getDocBySlug(slug)

  if (!doc) {
    notFound()
  }

  // Get backlinks for this document
  const backlinks = await getBacklinksForDoc(doc.slug)

  return (
    <article>
      {/* Breadcrumb */}
      <nav className="text-sm text-gray-600 mb-4">
        <ol className="flex items-center space-x-2">
          <li>
            <Link href="/docs" className="hover:text-gray-900">
              Docs
            </Link>
          </li>
          {slug.map((segment, index) => (
            <li key={segment} className="flex items-center">
              <span className="mx-2">/</span>
              <span className={index === slug.length - 1 ? 'text-gray-900' : ''}>
                {segment.replace(/-/g, ' ')}
              </span>
            </li>
          ))}
        </ol>
      </nav>

      {/* Document header */}
      <div className="mb-8 pb-8 border-b border-gray-200">
        <h1 className="text-4xl font-bold text-gray-900 mb-2">{doc.title}</h1>
        {doc.description && <p className="text-lg text-gray-600">{doc.description}</p>}
        <div className="flex items-center gap-4 mt-4 text-sm text-gray-500">
          {doc.lastModified && (
            <span>Last updated: {new Date(doc.lastModified).toLocaleDateString()}</span>
          )}
          {doc.readingTime && <span>• {doc.readingTime} min read</span>}
        </div>
      </div>

      {/* Markdown content with wiki features */}
      <DocPageClient content={doc.content} slug={doc.slug} backlinks={backlinks} />

      {/* Navigation links */}
      <div className="mt-12 pt-8 border-t border-gray-200">
        <div className="flex justify-between">
          {doc.prev && (
            <a
              href={`/docs/${doc.prev.slug}`}
              className="flex items-center text-blue-600 hover:text-blue-700"
            >
              <svg className="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M15 19l-7-7 7-7"
                />
              </svg>
              {doc.prev.title}
            </a>
          )}
          {doc.next && (
            <a
              href={`/docs/${doc.next.slug}`}
              className="flex items-center text-blue-600 hover:text-blue-700 ml-auto"
            >
              {doc.next.title}
              <svg className="w-5 h-5 ml-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M9 5l7 7-7 7"
                />
              </svg>
            </a>
          )}
        </div>
      </div>
    </article>
  )
}
