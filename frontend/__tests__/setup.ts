// Jest setup file for React tests
import '@testing-library/jest-dom'
import { TextEncoder, TextDecoder } from 'util'

// Polyfills for Node environment
global.TextEncoder = TextEncoder
global.TextDecoder = TextDecoder as any

// Mock next/navigation
jest.mock('next/navigation', () => ({
  useRouter: () => ({
    push: jest.fn(),
    replace: jest.fn(),
    prefetch: jest.fn(),
  }),
  useSearchParams: () => ({
    get: jest.fn(),
  }),
  usePathname: () => '',
}))

// Mock config
jest.mock('@/lib/config', () => ({
  appConfig: {
    api: {
      baseUrl: 'http://localhost:3000',
    },
  },
}))

// Mock fetch globally
global.fetch = jest.fn()

// Clean up after each test
afterEach(() => {
  jest.clearAllMocks()
})