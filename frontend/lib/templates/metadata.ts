export interface TemplateMetadata {
  id: string
  name: string
  description: string
  category: 'Basic' | 'I/O' | 'Network' | 'Computation' | 'Advanced' | 'Error Handling'
  filename: string
}

export const templateMetadata: TemplateMetadata[] = [
  {
    id: 'hello-world',
    name: 'Hello World',
    description: 'Basic Python program demonstrating output and variables',
    category: 'Basic',
    filename: 'hello-world.py'
  },
  {
    id: 'file-io',
    name: 'File I/O',
    description: 'Reading and writing files with error handling',
    category: 'I/O',
    filename: 'file-io.py'
  },
  {
    id: 'network-request',
    name: 'Network Request',
    description: 'Making HTTP requests and handling responses',
    category: 'Network',
    filename: 'network-request.py'
  },
  {
    id: 'cpu-intensive',
    name: 'CPU-Intensive Task',
    description: 'Prime number calculation with resource monitoring',
    category: 'Computation',
    filename: 'cpu-intensive.py'
  },
  {
    id: 'error-handling',
    name: 'Error Handling',
    description: 'Exception handling patterns and best practices',
    category: 'Error Handling',
    filename: 'error-handling.py'
  },
  {
    id: 'async-await',
    name: 'Async/Await',
    description: 'Asynchronous programming with asyncio',
    category: 'Advanced',
    filename: 'async-await.py'
  },
  {
    id: 'data-science',
    name: 'Data Science',
    description: 'Statistical analysis and data processing example',
    category: 'Computation',
    filename: 'data-science.py'
  },
  {
    id: 'long-running',
    name: 'Long-Running Process',
    description: 'Simulates a long-running task for testing monitoring and cancellation',
    category: 'Advanced',
    filename: 'long-running.py'
  }
]