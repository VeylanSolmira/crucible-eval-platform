'use client'

import { useCodeTemplates } from '@/hooks/useCodeTemplates'

interface CodeTemplateSelectorProps {
  onSelectTemplate: (code: string) => void
}

export function CodeTemplateSelector({ onSelectTemplate }: CodeTemplateSelectorProps) {
  const { templatesByCategory, loading, error } = useCodeTemplates()

  if (loading) {
    return <div className="p-4">Loading templates...</div>
  }

  if (error) {
    return <div className="p-4 text-red-600">Error loading templates: {error}</div>
  }

  return (
    <div className="p-4">
      <h3 className="text-lg font-semibold mb-4">Code Templates</h3>
      {Object.entries(templatesByCategory).map(([category, templates]) => (
        <div key={category} className="mb-6">
          <h4 className="text-sm font-medium text-gray-700 mb-2">{category}</h4>
          <div className="grid grid-cols-1 gap-2">
            {templates.map(template => (
              <button
                key={template.id}
                onClick={() => onSelectTemplate(template.code)}
                className="text-left p-3 border rounded-lg hover:bg-gray-50 transition-colors"
              >
                <div className="font-medium text-gray-900">{template.name}</div>
                <div className="text-sm text-gray-600">{template.description}</div>
              </button>
            ))}
          </div>
        </div>
      ))}
    </div>
  )
}
