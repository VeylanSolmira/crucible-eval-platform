// Application configuration
export const appConfig = {
  // Branding
  name: process.env.NEXT_PUBLIC_APP_NAME || 'Crucible Platform',
  title: process.env.NEXT_PUBLIC_APP_TITLE || 'Crucible Evaluation Platform', 
  description: process.env.NEXT_PUBLIC_APP_DESCRIPTION || 'Secure AI model evaluation platform with sandboxed execution',
  
  // Features
  features: {
    showSafetyWarning: process.env.NEXT_PUBLIC_SHOW_SAFETY_WARNING !== 'false',
    enableBatchSubmission: process.env.NEXT_PUBLIC_ENABLE_BATCH !== 'false',
    enableMonitoring: process.env.NEXT_PUBLIC_ENABLE_MONITORING !== 'false',
  },
  
  // API configuration (server-side)
  api: {
    baseUrl: process.env.API_URL || 'http://localhost:8080',
  },
  
  // Theme
  theme: {
    primaryColor: process.env.NEXT_PUBLIC_PRIMARY_COLOR || 'blue',
    logo: process.env.NEXT_PUBLIC_LOGO_EMOJI || '🚀',
  }
} as const

export type AppConfig = typeof appConfig