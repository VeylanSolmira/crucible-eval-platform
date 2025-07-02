import type { Metadata } from 'next'
import './globals.css'
import { appConfig } from '@/lib/config'
import { Providers } from './providers'

export const metadata: Metadata = {
  title: `${appConfig.name} - AI Evaluation`,
  description: appConfig.description,
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <head>
        <link rel="icon" href="/favicon.ico" sizes="any" />
        <link rel="icon" href="/favicon.svg" type="image/svg+xml" />
      </head>
      <body>
        <Providers>{children}</Providers>
      </body>
    </html>
  )
}
