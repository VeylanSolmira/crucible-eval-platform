/**
 * Documentation System Configuration
 * Controls how docs are loaded and served
 */

export interface DocsConfig {
  // Loading strategy
  loadingStrategy: 'static' | 'dynamic' | 'hybrid'
  
  // Cache settings
  cache: {
    enabled: boolean
    ttl: number // seconds
    maxSize: number // MB
  }
  
  // Build optimization
  build: {
    // Pre-render all pages at build time
    prerender: boolean
    // Include content in JS bundles vs separate chunks
    bundleContent: boolean
    // Generate search index at build time
    generateSearchIndex: boolean
  }
  
  // Runtime optimization
  runtime: {
    // Lazy load images and diagrams
    lazyLoadMedia: boolean
    // Prefetch linked pages
    prefetchLinks: boolean
    // Use service worker for offline support
    enableOffline: boolean
  }
}

// Development config - fast iteration
const devConfig: DocsConfig = {
  loadingStrategy: 'static',
  cache: {
    enabled: false,
    ttl: 0,
    maxSize: 0
  },
  build: {
    prerender: false,
    bundleContent: true,
    generateSearchIndex: false
  },
  runtime: {
    lazyLoadMedia: false,
    prefetchLinks: false,
    enableOffline: false
  }
}

// Production config - optimized for performance
const prodConfig: DocsConfig = {
  loadingStrategy: 'static',
  cache: {
    enabled: true,
    ttl: 3600, // 1 hour
    maxSize: 50 // 50MB
  },
  build: {
    prerender: true,
    bundleContent: false, // Use dynamic imports
    generateSearchIndex: true
  },
  runtime: {
    lazyLoadMedia: true,
    prefetchLinks: true,
    enableOffline: true
  }
}

// Future API-based config (when needed)
const apiConfig: DocsConfig = {
  loadingStrategy: 'dynamic',
  cache: {
    enabled: true,
    ttl: 300, // 5 minutes
    maxSize: 100
  },
  build: {
    prerender: false,
    bundleContent: false,
    generateSearchIndex: false
  },
  runtime: {
    lazyLoadMedia: true,
    prefetchLinks: true,
    enableOffline: false
  }
}

export function getDocsConfig(): DocsConfig {
  if (process.env.DOCS_STRATEGY === 'api') {
    return apiConfig
  }
  
  return process.env.NODE_ENV === 'production' ? prodConfig : devConfig
}