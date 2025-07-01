/** @type {import('next').NextConfig} */
const nextConfig = {
  output: 'standalone',
  
  // Increase timeout for static generation
  staticPageGenerationTimeout: 240, // 4 minutes
  
  // Reduce build parallelism
  experimental: {
    workerThreads: false,
    cpus: 2
  },
  
  // API routes will be proxied to backend
  async rewrites() {
    // For Docker, use the service name; for local dev, use localhost
    const apiUrl = process.env.API_URL || 'http://api-service:8080'
    return [
      {
        source: '/api/:path*',
        destination: `${apiUrl}/api/:path*`,
      },
    ]
  },
  // Security headers
  async headers() {
    return [
      {
        source: '/:path*',
        headers: [
          {
            key: 'X-Frame-Options',
            value: 'DENY',
          },
          {
            key: 'X-Content-Type-Options',
            value: 'nosniff',
          },
          {
            key: 'X-XSS-Protection',
            value: '1; mode=block',
          },
        ],
      },
    ]
  },
}

module.exports = nextConfig