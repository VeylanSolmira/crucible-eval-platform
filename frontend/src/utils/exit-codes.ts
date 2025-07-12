/**
 * Utility functions for interpreting container exit codes
 */

export interface ExitCodeInfo {
  code: number
  message: string
  description: string
  type: 'success' | 'error' | 'warning'
}

/**
 * Get human-friendly interpretation of container exit codes
 */
export function getExitCodeInfo(exitCode: number): ExitCodeInfo {
  switch (exitCode) {
    case 0:
      return {
        code: 0,
        message: 'Success',
        description: 'Process completed successfully',
        type: 'success',
      }

    case 1:
      return {
        code: 1,
        message: 'General Error',
        description: 'Process failed with an error',
        type: 'error',
      }

    case 2:
      return {
        code: 2,
        message: 'Misuse of Shell Command',
        description: 'Incorrect command usage or syntax error',
        type: 'error',
      }

    case 124:
      return {
        code: 124,
        message: 'Timeout',
        description: 'Process exceeded the 30-second time limit',
        type: 'warning',
      }

    case 125:
      return {
        code: 125,
        message: 'Command Failed',
        description: 'Container command could not be invoked',
        type: 'error',
      }

    case 126:
      return {
        code: 126,
        message: 'Command Not Executable',
        description: 'Command found but not executable',
        type: 'error',
      }

    case 127:
      return {
        code: 127,
        message: 'Command Not Found',
        description: 'Command or interpreter not found',
        type: 'error',
      }

    case 137:
      return {
        code: 137,
        message: 'Memory Limit Exceeded',
        description: 'Process killed due to exceeding 512MB memory limit (OOM)',
        type: 'error',
      }

    case 139:
      return {
        code: 139,
        message: 'Segmentation Fault',
        description: 'Process crashed due to invalid memory access',
        type: 'error',
      }

    case 143:
      return {
        code: 143,
        message: 'Terminated',
        description: 'Process was terminated by SIGTERM signal',
        type: 'warning',
      }

    default:
      // Handle other signal-based exit codes (128 + signal number)
      if (exitCode > 128 && exitCode < 165) {
        const signalNum = exitCode - 128
        return {
          code: exitCode,
          message: `Killed by Signal ${signalNum}`,
          description: `Process terminated by signal ${signalNum}`,
          type: 'error',
        }
      }

      // Unknown exit code
      return {
        code: exitCode,
        message: 'Unknown Error',
        description: `Process exited with code ${exitCode}`,
        type: 'error',
      }
  }
}

/**
 * Get a short badge-friendly version of the exit code message
 */
export function getExitCodeBadge(exitCode: number): string {
  // Special cases for common codes
  switch (exitCode) {
    case 0:
      return '✓'
    case 137:
      return 'OOM'
    case 124:
    case 143:
      return 'Timeout'
    default:
      return `Exit ${exitCode}`
  }
}

/**
 * Get color classes for exit code display
 */
export function getExitCodeColorClasses(exitCode: number): {
  bg: string
  text: string
  border?: string
} {
  const info = getExitCodeInfo(exitCode)

  switch (info.type) {
    case 'success':
      return {
        bg: 'bg-green-100',
        text: 'text-green-700',
        border: 'border-green-200',
      }
    case 'warning':
      return {
        bg: 'bg-yellow-100',
        text: 'text-yellow-700',
        border: 'border-yellow-200',
      }
    case 'error':
    default:
      return {
        bg: 'bg-red-100',
        text: 'text-red-700',
        border: 'border-red-200',
      }
  }
}