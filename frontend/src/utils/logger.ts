/**
 * Frontend logger utility with configurable log levels
 * Uses console methods but allows filtering based on environment
 */

export enum LogLevel {
  DEBUG = 0,
  INFO = 1,
  WARN = 2,
  ERROR = 3,
  NONE = 4,
}

export interface LoggerConfig {
  level: LogLevel
  includeTimestamp: boolean
  includePrefix: boolean
}

class Logger {
  private config: LoggerConfig

  constructor() {
    // Default configuration based on environment
    this.config = {
      level: this.getDefaultLogLevel(),
      includeTimestamp: process.env.NODE_ENV === 'development',
      includePrefix: true,
    }

    // Allow runtime configuration via localStorage in browser
    if (typeof window !== 'undefined') {
      this.loadBrowserConfig()
    }
  }

  private getDefaultLogLevel(): LogLevel {
    if (process.env.NODE_ENV === 'production') {
      return LogLevel.ERROR
    }
    
    // Check for explicit log level in env
    const envLevel = process.env.NEXT_PUBLIC_LOG_LEVEL?.toUpperCase()
    if (envLevel && envLevel in LogLevel) {
      return LogLevel[envLevel as keyof typeof LogLevel]
    }
    
    return LogLevel.INFO
  }

  private loadBrowserConfig() {
    try {
      const stored = localStorage.getItem('logger-config')
      if (stored) {
        const config = JSON.parse(stored) as Partial<LoggerConfig>
        this.config = { ...this.config, ...config }
      }
    } catch {
      // Ignore errors, use defaults
    }
  }

  private formatMessage(level: string, message: string, ...args: unknown[]): unknown[] {
    const parts: unknown[] = []
    
    if (this.config.includePrefix) {
      parts.push(`[${level}]`)
    }
    
    parts.push(message)
    
    if (this.config.includeTimestamp) {
      parts.push(new Date().toISOString())
    }
    
    return [...parts, ...args]
  }

  debug(message: string, ...args: unknown[]) {
    if (this.config.level <= LogLevel.DEBUG) {
      console.log(...this.formatMessage('DEBUG', message, ...args))
    }
  }

  info(message: string, ...args: unknown[]) {
    if (this.config.level <= LogLevel.INFO) {
      console.info(...this.formatMessage('INFO', message, ...args))
    }
  }

  warn(message: string, ...args: unknown[]) {
    if (this.config.level <= LogLevel.WARN) {
      console.warn(...this.formatMessage('WARN', message, ...args))
    }
  }

  error(message: string, ...args: unknown[]) {
    if (this.config.level <= LogLevel.ERROR) {
      console.error(...this.formatMessage('ERROR', message, ...args))
    }
  }

  // Group related logs
  group(label: string, fn: () => void) {
    if (this.config.level < LogLevel.NONE) {
      console.group(label)
      try {
        fn()
      } finally {
        console.groupEnd()
      }
    }
  }

  // Time operations
  time(label: string): () => void {
    if (this.config.level <= LogLevel.DEBUG) {
      console.time(label)
      return () => console.timeEnd(label)
    }
    return () => {} // no-op
  }

  // Runtime configuration
  setLevel(level: LogLevel) {
    this.config.level = level
    this.saveBrowserConfig()
  }

  configure(config: Partial<LoggerConfig>) {
    this.config = { ...this.config, ...config }
    this.saveBrowserConfig()
  }

  private saveBrowserConfig() {
    if (typeof window !== 'undefined') {
      try {
        localStorage.setItem('logger-config', JSON.stringify(this.config))
      } catch {
        // Ignore errors
      }
    }
  }

  // Utility to expose logger config in development
  getConfig(): LoggerConfig {
    return { ...this.config }
  }
}

// Create singleton instance
export const logger = new Logger()

// Convenience exports
export const log = {
  debug: logger.debug.bind(logger),
  info: logger.info.bind(logger),
  warn: logger.warn.bind(logger),
  error: logger.error.bind(logger),
  group: logger.group.bind(logger),
  time: logger.time.bind(logger),
}

// Export logger instance for advanced usage
export default logger

// Development helpers - only available in dev mode
if (process.env.NODE_ENV === 'development' && typeof window !== 'undefined') {
  // Expose logger on window for debugging
  (window as { __logger?: Logger }).__logger = logger
  
  // Log current configuration
  console.info('Logger initialized with config:', logger.getConfig())
}