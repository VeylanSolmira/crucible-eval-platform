import Link from 'next/link'
import type { Metadata } from 'next'

export const metadata: Metadata = {
  title: '404 - Page Not Found | Crucible Platform',
  description: 'The page you are looking for could not be found.',
}

export default function NotFound() {
  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center px-4">
      <div className="max-w-2xl w-full text-center">
        {/* 404 Icon/Illustration */}
        <div className="mb-8">
          <div className="text-9xl font-bold text-gray-300">404</div>
        </div>

        {/* Error Message */}
        <h1 className="text-3xl font-bold text-gray-900 mb-4">
          Page Not Found
        </h1>
        <p className="text-lg text-gray-600 mb-8">
          Sorry, we couldn&apos;t find the page you&apos;re looking for. 
          It might have been moved, deleted, or never existed.
        </p>

        {/* Helpful Links */}
        <div className="space-y-4">
          <div className="flex flex-col sm:flex-row gap-4 justify-center">
            <Link
              href="/"
              className="inline-flex items-center px-6 py-3 bg-blue-600 text-white font-medium rounded-lg hover:bg-blue-700 transition-colors"
            >
              Go to Homepage
            </Link>
            <Link
              href="/docs"
              className="inline-flex items-center px-6 py-3 bg-gray-200 text-gray-900 font-medium rounded-lg hover:bg-gray-300 transition-colors"
            >
              Browse Documentation
            </Link>
          </div>

          {/* Popular Pages */}
          <div className="mt-12">
            <h2 className="text-sm font-semibold text-gray-500 uppercase tracking-wide mb-4">
              Popular Pages
            </h2>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 max-w-md mx-auto">
              <Link href="/docs/quickstart" className="text-blue-600 hover:text-blue-700">
                Quick Start Guide →
              </Link>
              <Link href="/docs/architecture" className="text-blue-600 hover:text-blue-700">
                Architecture Overview →
              </Link>
              <Link href="/storage" className="text-blue-600 hover:text-blue-700">
                Storage Explorer →
              </Link>
              <Link href="/slides" className="text-blue-600 hover:text-blue-700">
                Platform Slides →
              </Link>
            </div>
          </div>

          {/* Search Suggestion */}
          <div className="mt-8 p-6 bg-white rounded-lg shadow-sm border border-gray-200">
            <p className="text-gray-700 mb-2">
              💡 <strong>Tip:</strong> If you&apos;re looking for specific documentation, 
              try browsing our <Link href="/docs" className="text-blue-600 hover:text-blue-700">docs index</Link> or 
              use the search feature.
            </p>
          </div>
        </div>

        {/* Optional: Report Issue */}
        <div className="mt-12 text-sm text-gray-500">
          Think this is a mistake? 
          <a 
            href="https://github.com/your-repo/issues" 
            className="text-blue-600 hover:text-blue-700 ml-1"
            target="_blank"
            rel="noopener noreferrer"
          >
            Report an issue
          </a>
        </div>
      </div>
    </div>
  )
}