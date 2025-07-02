// Storage backend types

export interface RedisDetails {
  backend: string
  status: string
  info: {
    keys: string[]
    memory: Record<string, any>
    stats: Record<string, any>
  }
}

export interface DatabaseDetails {
  backend: string
  connection: string
  tables: {
    evaluations: {
      count: number
      by_status: Record<string, number>
      columns: string[]
    }
    evaluation_events: {
      count: number
      columns: string[]
    }
  }
  recent_evaluations: Array<{
    id: string
    code: string
    language: string
    status: string
    created_at?: string
    completed_at?: string
    output?: string
    error?: string
  }>
}

export interface FileSystemDetails {
  backend: string
  status: string
  path: string
  stats: {
    total_evaluations: number
    by_status: Record<string, number>
    recent_files: string[]
  }
}

export interface StorageOverview {
  backends: {
    name: string
    type: string
    status: 'healthy' | 'degraded' | 'down'
    details: string
  }[]
  statistics: {
    total_evaluations: number
    evaluations_24h: number
    success_rate: number
    avg_execution_time: number
  }
}
