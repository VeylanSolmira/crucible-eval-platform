import Link from 'next/link'
import { getAllDocs } from '@/lib/docs'

export default async function DocsNotFound() {
  // Get all docs to suggest similar pages
  const allDocs = await getAllDocs()
  
  // Get the most recent docs as suggestions
  const recentDocs = allDocs
    .sort((a, b) => new Date(b.lastModified || 0).getTime() - new Date(a.lastModified || 0).getTime())
    .slice(0, 5)

  return (
    <div className="max-w-4xl mx-auto py-12 px-6">
      <div className="text-center mb-12">
        <h1 className="text-4xl font-bold text-gray-900 mb-4">
          Documentation Page Not Found
        </h1>
        <p className="text-lg text-gray-600">
          The documentation page you&apos;re looking for doesn&apos;t exist or has been moved.
        </p>
      </div>

      {/* Quick Actions */}
      <div className="bg-blue-50 border border-blue-200 rounded-lg p-6 mb-8">
        <h2 className="text-lg font-semibold text-blue-900 mb-3">
          🔍 Looking for something specific?
        </h2>
        <div className="space-y-2">
          <p className="text-blue-800">
            • Check the <Link href="/docs" className="font-medium underline hover:no-underline">documentation index</Link> for all available pages
          </p>
          <p className="text-blue-800">
            • Browse our <Link href="/docs/quickstart" className="font-medium underline hover:no-underline">quickstart guide</Link> to get started
          </p>
          <p className="text-blue-800">
            • View the <Link href="/docs/architecture" className="font-medium underline hover:no-underline">architecture overview</Link> for system design
          </p>
        </div>
      </div>

      {/* Recent Documentation */}
      {recentDocs.length > 0 && (
        <div className="mb-12">
          <h2 className="text-xl font-semibold text-gray-900 mb-4">
            Recent Documentation
          </h2>
          <div className="grid gap-4">
            {recentDocs.map((doc) => (
              <Link
                key={doc.slug}
                href={`/docs/${doc.slug}`}
                className="block p-4 bg-white rounded-lg border border-gray-200 hover:border-blue-300 hover:shadow-md transition-all"
              >
                <h3 className="font-medium text-gray-900 mb-1">{doc.title}</h3>
                {doc.description && (
                  <p className="text-sm text-gray-600">{doc.description}</p>
                )}
              </Link>
            ))}
          </div>
        </div>
      )}

      {/* Wiki Links Note */}
      <div className="bg-gray-100 rounded-lg p-6 mb-8">
        <h3 className="font-medium text-gray-900 mb-2">
          📝 Note about Wiki Links
        </h3>
        <p className="text-gray-700 text-sm">
          If you arrived here from a wiki link [[like this]], the page might not have been created yet. 
          Wiki links are automatically detected but the target pages need to be manually created.
        </p>
      </div>

      {/* Back Navigation */}
      <div className="flex justify-center">
        <Link
          href="/docs"
          className="inline-flex items-center px-6 py-3 bg-gray-900 text-white font-medium rounded-lg hover:bg-gray-800 transition-colors"
        >
          ← Back to Documentation
        </Link>
      </div>
    </div>
  )
}