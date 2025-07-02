import Link from 'next/link'

export default function DocsHome() {
  return (
    <div className="prose prose-gray max-w-none">
      <h1>Crucible Platform Documentation</h1>

      <p className="lead">
        Welcome to the comprehensive documentation for the Crucible Platform - a secure code
        evaluation system designed for AI safety research.
      </p>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 not-prose mt-8">
        <Link
          href="/docs/getting-started/quickstart"
          className="block p-6 bg-white rounded-lg shadow-sm border border-gray-200 hover:shadow-md transition-shadow"
        >
          <h3 className="text-lg font-semibold text-gray-900 mb-2">🚀 Quick Start</h3>
          <p className="text-gray-600">Get up and running with Crucible in under 5 minutes</p>
        </Link>

        <Link
          href="/docs/architecture/platform-overview"
          className="block p-6 bg-white rounded-lg shadow-sm border border-gray-200 hover:shadow-md transition-shadow"
        >
          <h3 className="text-lg font-semibold text-gray-900 mb-2">🏗️ Architecture</h3>
          <p className="text-gray-600">Understand the platform&apos;s microservices design</p>
        </Link>

        <Link
          href="/docs/api/endpoints"
          className="block p-6 bg-white rounded-lg shadow-sm border border-gray-200 hover:shadow-md transition-shadow"
        >
          <h3 className="text-lg font-semibold text-gray-900 mb-2">📡 API Reference</h3>
          <p className="text-gray-600">Complete API documentation with examples</p>
        </Link>

        <Link
          href="/docs/deployment/docker"
          className="block p-6 bg-white rounded-lg shadow-sm border border-gray-200 hover:shadow-md transition-shadow"
        >
          <h3 className="text-lg font-semibold text-gray-900 mb-2">🚢 Deployment</h3>
          <p className="text-gray-600">Deploy to Docker, AWS, or Kubernetes</p>
        </Link>
      </div>

      <h2 className="mt-12">Platform Overview</h2>

      <p>
        The Crucible Platform provides a secure, scalable environment for executing untrusted code
        as part of AI model evaluation workflows. Built with security-first principles, it offers:
      </p>

      <ul>
        <li>
          🔒 <strong>Secure Isolation</strong> - Each evaluation runs in an isolated container
        </li>
        <li>
          ⚡ <strong>Real-time Monitoring</strong> - Stream output as code executes
        </li>
        <li>
          📊 <strong>Horizontal Scaling</strong> - Add executors to handle more load
        </li>
        <li>
          🔍 <strong>Complete Observability</strong> - Track every evaluation and its results
        </li>
        <li>
          🛡️ <strong>Defense in Depth</strong> - Multiple layers of security controls
        </li>
      </ul>

      <h2>Key Features</h2>

      <h3>For Researchers</h3>
      <ul>
        <li>Submit Python code for evaluation</li>
        <li>Real-time output streaming</li>
        <li>Batch evaluation support</li>
        <li>Result history and analysis</li>
      </ul>

      <h3>For Platform Engineers</h3>
      <ul>
        <li>Microservices architecture</li>
        <li>Container orchestration</li>
        <li>Comprehensive monitoring</li>
        <li>Infrastructure as Code</li>
      </ul>

      <h3>For Security Teams</h3>
      <ul>
        <li>Network isolation</li>
        <li>Resource limits</li>
        <li>Audit logging</li>
        <li>Threat detection</li>
      </ul>

      <div className="bg-blue-50 border border-blue-200 rounded-lg p-6 mt-8">
        <h3 className="text-lg font-semibold text-blue-900 mb-2">🎓 Learning Platform</h3>
        <p className="text-blue-800">
          This documentation serves a dual purpose: operational reference and educational resource.
          Each section includes architectural decisions, trade-offs, and implementation details to
          help you understand not just <em>what</em> we built, but <em>why</em> we built it this
          way.
        </p>
      </div>
    </div>
  )
}
