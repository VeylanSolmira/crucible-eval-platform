'use client'

import React, { useEffect, useRef } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import remarkWikiLink from 'remark-wiki-link'
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter'
import { vscDarkPlus } from 'react-syntax-highlighter/dist/cjs/styles/prism'
import { useRouter } from 'next/navigation'

interface MarkdownRendererProps {
  content: string
  className?: string
  enableMermaid?: boolean
}

export function MarkdownRenderer({ 
  content, 
  className = '',
  enableMermaid = true 
}: MarkdownRendererProps) {
  const contentRef = useRef<HTMLDivElement>(null)
  const router = useRouter()

  useEffect(() => {
    // Handle Mermaid diagrams if enabled
    if (enableMermaid && contentRef.current) {
      // Dynamically import mermaid only when needed
      void import('mermaid').then(({ default: mermaid }) => {
        mermaid.initialize({ 
          startOnLoad: true,
          theme: 'default',
          themeVariables: {
            primaryColor: '#3b82f6',
            primaryTextColor: '#fff',
            primaryBorderColor: '#2563eb',
            lineColor: '#6b7280',
            secondaryColor: '#f3f4f6',
            tertiaryColor: '#e5e7eb',
          }
        })

        // Process mermaid blocks after markdown rendering
        const processedNodes = new Set<Element>()
        
        const processMermaidBlocks = () => {
          const codeBlocks = contentRef.current!.querySelectorAll('code')
          codeBlocks.forEach((block) => {
            // Check if this is a mermaid block and hasn't been processed
            if (block.textContent?.startsWith('graph') || 
                block.textContent?.startsWith('sequenceDiagram') ||
                block.textContent?.startsWith('classDiagram')) {
              
              const parent = block.parentElement
              if (parent && !processedNodes.has(parent)) {
                processedNodes.add(parent)
                
                try {
                  const graphDefinition = block.textContent || ''
                  const graphId = `mermaid-${Date.now()}-${Math.random()}`
                  
                  // Create a div to hold the rendered diagram
                  const div = document.createElement('div')
                  div.id = graphId
                  div.className = 'mermaid-diagram my-4 flex justify-center'
                  
                  // Replace the code block with the div
                  parent.replaceWith(div)
                  
                  // Render the diagram
                  void mermaid.render(graphId, graphDefinition).then((result) => {
                    div.innerHTML = result.svg
                  })
                } catch (error) {
                  console.error('Mermaid rendering error:', error)
                }
              }
            }
          })
        }
        
        // Small delay to ensure React has rendered
        setTimeout(processMermaidBlocks, 100)
      })
    }
  }, [content, enableMermaid])

  return (
    <div ref={contentRef} className={`markdown-content ${className}`}>
      <ReactMarkdown
        remarkPlugins={[
          remarkGfm,
          [remarkWikiLink, {
            pageResolver: (name: string) => [
              name.toLowerCase().replace(/\s+/g, '-')
            ],
            hrefTemplate: (permalink: string) => `/docs/${permalink}`,
            wikiLinkClassName: 'wiki-link',
            newClassName: 'wiki-link-new'
          }]
        ]}
        components={{
          a: ({ href, children, className, ...props }: { 
            href?: string; 
            children?: React.ReactNode; 
            className?: string;
            [key: string]: any;
          }) => {
            // Handle wiki links
            if (className?.includes('wiki-link')) {
              const isNew = className.includes('wiki-link-new')
              return (
                <a
                  href={href}
                  className={`${isNew ? 'text-red-600 hover:text-red-700' : 'text-blue-600 hover:text-blue-700'} underline font-medium`}
                  onClick={(e) => {
                    e.preventDefault()
                    router.push(href)
                  }}
                  {...props}
                >
                  {children}
                  {isNew && <span className="text-xs ml-1">[?]</span>}
                </a>
              )
            }
            // Regular links
            return (
              <a
                href={href}
                className="text-blue-600 hover:text-blue-700 underline"
                {...props}
              >
                {children}
              </a>
            )
          },
          code({ node, inline, className, children, ...props }: {
            node?: any;
            inline?: boolean;
            className?: string;
            children?: React.ReactNode;
            [key: string]: any;
          }) {
            const match = /language-(\w+)/.exec(className || '')
            const language = match ? match[1] : ''
            
            // Special handling for mermaid
            if (language === 'mermaid' && enableMermaid) {
              return (
                <code className={className} {...props}>
                  {children}
                </code>
              )
            }
            
            return !inline && match ? (
              <SyntaxHighlighter
                language={language}
                style={vscDarkPlus}
                PreTag="div"
                {...props}
              >
                {String(children).replace(/\n$/, '')}
              </SyntaxHighlighter>
            ) : (
              <code className={className} {...props}>
                {children}
              </code>
            )
          }
        }}
      >
        {content}
      </ReactMarkdown>
    </div>
  )
}