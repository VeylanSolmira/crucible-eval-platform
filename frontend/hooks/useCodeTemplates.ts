import { useState, useEffect } from 'react'
import { CodeTemplate } from '@/lib/templates/loader'

export function useCodeTemplates() {
  const [templates, setTemplates] = useState<CodeTemplate[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    fetchTemplates()
  }, [])

  const fetchTemplates = async () => {
    try {
      const response = await fetch('/app/templates')
      if (!response.ok) {
        throw new Error('Failed to fetch templates')
      }
      const data = await response.json()
      setTemplates(data)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error')
    } finally {
      setLoading(false)
    }
  }

  const getTemplatesByCategory = () => {
    return templates.reduce((acc, template) => {
      const category = template.category
      if (!acc[category]) {
        acc[category] = []
      }
      acc[category]!.push(template)
      return acc
    }, {} as Record<string, CodeTemplate[]>)
  }

  return {
    templates,
    templatesByCategory: getTemplatesByCategory(),
    loading,
    error,
    refetch: fetchTemplates
  }
}