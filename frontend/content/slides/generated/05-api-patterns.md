---
title: "API Patterns & Best Practices"
order: 5
tags: ["api", "patterns", "react"]
---

# API Patterns & Best Practices

## Making API Calls

```typescript
// Always handle both success and error
const { data, error } = await apiClient.submitEvaluation(request)

if (error) {
  console.error('API error:', error.message)
  return
}

// TypeScript knows data is defined here
console.log('Evaluation ID:', data.eval_id)
```

---

## React Component Pattern

```typescript
function EvaluationStatus({ evalId }: { evalId: string }) {
  const [status, setStatus] = useState<EvaluationStatus | null>(null)
  
  useEffect(() => {
    async function checkStatus() {
      const { data, error } = await apiClient.getEvaluationStatus(evalId)
      if (data) setStatus(data)
    }
    checkStatus()
  }, [evalId])
  
  return <div>{status?.output}</div>
}
```

---

## Error Handling

```typescript
try {
  const { data, error } = await apiClient.submitEvaluation(code)
  
  if (error) {
    // API returned an error
    showError(error.message)
    return
  }
  
  // Success!
  processResult(data)
} catch (e) {
  // Network or unexpected error
  showError('Network error')
}
```

---

## Custom Hooks

```typescript
// Reusable evaluation hook
export function useEvaluation(evalId: string) {
  const [status, setStatus] = useState<EvaluationStatus>()
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string>()

  useEffect(() => {
    // Polling logic here
  }, [evalId])

  return { status, loading, error }
}
```