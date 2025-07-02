'use client'

import React, { useState } from 'react'
import Link from 'next/link'
import { usePathname } from 'next/navigation'
import './docs.css'

interface NavItem {
  title: string
  href?: string
  children?: NavItem[]
}

// Documentation navigation structure
const navigation: NavItem[] = [
  {
    title: 'Getting Started',
    children: [
      { title: 'Quick Start', href: '/docs/getting-started/quickstart' },
      { title: 'Installation', href: '/docs/getting-started/installation' },
      { title: 'Configuration', href: '/docs/getting-started/configuration' },
    ],
  },
  {
    title: 'Architecture',
    children: [
      { title: 'Platform Overview', href: '/docs/architecture/platform-overview' },
      { title: 'Microservices Design', href: '/docs/architecture/microservices' },
      { title: 'Security Model', href: '/docs/architecture/security' },
      { title: 'Event Architecture', href: '/docs/architecture/events' },
    ],
  },
  {
    title: 'API Reference',
    children: [
      { title: 'Endpoints', href: '/docs/api/endpoints' },
      { title: 'Authentication', href: '/docs/api/authentication' },
      { title: 'WebSocket Events', href: '/docs/api/websockets' },
      { title: 'Error Handling', href: '/docs/api/errors' },
    ],
  },
  {
    title: 'Deployment',
    children: [
      { title: 'Docker Compose', href: '/docs/deployment/docker' },
      { title: 'AWS EC2', href: '/docs/deployment/ec2' },
      { title: 'Kubernetes', href: '/docs/deployment/kubernetes' },
      { title: 'SSL & Certificates', href: '/docs/deployment/ssl' },
    ],
  },
  {
    title: 'Development',
    children: [
      { title: 'Local Setup', href: '/docs/development/local-setup' },
      { title: 'Testing', href: '/docs/development/testing' },
      { title: 'Contributing', href: '/docs/development/contributing' },
      { title: 'Code Style', href: '/docs/development/code-style' },
    ],
  },
  {
    title: 'Frontend',
    children: [
      { title: 'Component Guide', href: '/docs/frontend/components' },
      { title: 'React Query Patterns', href: '/docs/frontend/react-query' },
      { title: 'Type Safety', href: '/docs/frontend/typescript' },
      { title: 'UX Principles', href: '/docs/frontend/ux-principles' },
    ],
  },
  {
    title: 'Security',
    children: [
      { title: 'Container Isolation', href: '/docs/security/containers' },
      { title: 'Network Policies', href: '/docs/security/network' },
      { title: 'Threat Model', href: '/docs/security/threats' },
      { title: 'Best Practices', href: '/docs/security/best-practices' },
    ],
  },
]

function NavSection({ item, isActive }: { item: NavItem; isActive: (href: string) => boolean }) {
  const [isOpen, setIsOpen] = useState(true)

  if (item.href) {
    return (
      <Link
        href={item.href}
        className={`block px-4 py-2 text-sm rounded-md transition-colors ${
          isActive(item.href)
            ? 'bg-blue-50 text-blue-700 font-medium'
            : 'text-gray-700 hover:bg-gray-50'
        }`}
      >
        {item.title}
      </Link>
    )
  }

  return (
    <div className="mb-4">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center justify-between w-full px-4 py-2 text-sm font-medium text-gray-900 hover:bg-gray-50 rounded-md"
      >
        {item.title}
        <svg
          className={`w-4 h-4 transition-transform ${isOpen ? 'rotate-90' : ''}`}
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
        </svg>
      </button>
      {isOpen && item.children && (
        <div className="mt-1 ml-3 space-y-1">
          {item.children.map(child => (
            <NavSection key={child.href || child.title} item={child} isActive={isActive} />
          ))}
        </div>
      )}
    </div>
  )
}

export default function DocsLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname()
  const [searchQuery, setSearchQuery] = useState('')
  const [isMobileNavOpen, setIsMobileNavOpen] = useState(false)

  const isActive = (href: string) => pathname === href

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white shadow-sm border-b border-gray-200 sticky top-0 z-10">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-16">
            <div className="flex items-center">
              <Link href="/" className="text-xl font-bold text-gray-900 mr-8">
                ⚡ Crucible
              </Link>
              <nav className="hidden md:flex space-x-6">
                <Link href="/docs" className="text-gray-700 hover:text-gray-900">
                  Docs
                </Link>
                <Link href="/" className="text-gray-700 hover:text-gray-900">
                  Platform
                </Link>
                <Link href="/storage" className="text-gray-700 hover:text-gray-900">
                  Storage
                </Link>
                <a
                  href="https://github.com/your-repo/crucible"
                  className="text-gray-700 hover:text-gray-900"
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  GitHub
                </a>
              </nav>
            </div>

            {/* Mobile menu button */}
            <button
              onClick={() => setIsMobileNavOpen(!isMobileNavOpen)}
              className="md:hidden p-2 rounded-md text-gray-700 hover:bg-gray-100"
            >
              <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d={isMobileNavOpen ? 'M6 18L18 6M6 6l12 12' : 'M4 6h16M4 12h16M4 18h16'}
                />
              </svg>
            </button>
          </div>
        </div>
      </header>

      <div className="flex">
        {/* Sidebar */}
        <aside
          className={`${
            isMobileNavOpen ? 'block' : 'hidden'
          } md:block w-64 bg-white border-r border-gray-200 min-h-screen fixed md:sticky top-16 overflow-y-auto`}
        >
          <div className="p-4">
            {/* Search */}
            <div className="mb-6">
              <input
                type="text"
                placeholder="Search docs..."
                value={searchQuery}
                onChange={e => setSearchQuery(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              />
            </div>

            {/* Navigation */}
            <nav className="space-y-2">
              {navigation.map(section => (
                <NavSection key={section.title} item={section} isActive={isActive} />
              ))}
            </nav>
          </div>
        </aside>

        {/* Main content */}
        <main className="flex-1 md:ml-64">
          <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-8">{children}</div>
        </main>
      </div>
    </div>
  )
}
