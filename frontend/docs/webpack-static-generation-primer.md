# Webpack and Static Generation Primer

## Overview

This primer explains how webpack and Next.js static generation work together to optimize content delivery in production.

## 1. What is Webpack?

Webpack is a **module bundler** that takes your code and its dependencies and packages them into optimized bundles for the browser.

### Key Concepts:

**Entry Points**: Where webpack starts building the dependency graph
```javascript
// webpack.config.js
module.exports = {
  entry: './src/index.js'  // Start here
}
```

**Loaders**: Transform files as they're imported
```javascript
// This allows: import styles from './app.css'
{
  test: /\.css$/,
  use: ['style-loader', 'css-loader']
}
```

**Plugins**: Perform wider operations
```javascript
plugins: [
  new HtmlWebpackPlugin(),  // Generate HTML files
  new MiniCssExtractPlugin() // Extract CSS to files
]
```

## 2. How Next.js Uses Webpack

Next.js comes with webpack pre-configured but extends it for:

### File-based Routing
```
pages/index.js → /
pages/about.js → /about
pages/blog/[slug].js → /blog/:slug
```

### Automatic Code Splitting
Each page gets its own bundle:
```
/.next/static/chunks/pages/index-abc123.js
/.next/static/chunks/pages/about-def456.js
```

### Module Imports
```javascript
// Next.js webpack config handles these special imports:
import Image from 'next/image'  // Optimized images
import dynamic from 'next/dynamic'  // Dynamic imports
```

## 3. Static Generation in Next.js

### Build Time vs Runtime

**Static Generation (SSG)**: HTML generated at build time
```javascript
// This runs at BUILD TIME, not when users visit
export async function getStaticProps() {
  const data = await fetchData()
  return { props: { data } }
}
```

**Server-Side Rendering (SSR)**: HTML generated per request
```javascript
// This runs on EVERY REQUEST
export async function getServerSideProps() {
  const data = await fetchData()
  return { props: { data } }
}
```

### Why Static Generation for Slides?

1. **Performance**: Pre-built HTML loads instantly
2. **Scalability**: Serves from CDN, no server needed
3. **Reliability**: No database = no database failures

## 4. Practical Example: Loading Markdown Files

### Development Mode
```javascript
// lib/slides/loader.ts
import fs from 'fs'
import path from 'path'

export async function loadSlide(id: string) {
  // In development, read directly from filesystem
  const filePath = path.join(process.cwd(), 'content/slides', `${id}.md`)
  const content = fs.readFileSync(filePath, 'utf8')
  return content
}
```

### Production Mode - Option 1: Static Imports
```javascript
// Webpack bundles these at build time
export async function loadSlide(id: string) {
  const slides = {
    'genesis': () => import('../../content/slides/01-genesis.md'),
    'evolution': () => import('../../content/slides/02-evolution.md'),
    // ... webpack creates separate chunks for each
  }
  
  const module = await slides[id]()
  return module.default
}
```

### Production Mode - Option 2: getStaticProps
```javascript
// pages/slides/[id].js
export async function getStaticPaths() {
  // Tell Next.js which slide pages to generate
  const slides = ['genesis', 'evolution', 'docker-journey']
  return {
    paths: slides.map(id => ({ params: { id } })),
    fallback: false
  }
}

export async function getStaticProps({ params }) {
  // This runs at build time for each slide
  const slideContent = await loadSlide(params.id)
  return {
    props: { slideContent }
  }
}
```

## 5. Build Process Flow

```
1. npm run build
   ↓
2. Next.js invokes webpack
   ↓
3. Webpack processes all imports
   ↓
4. For each page with getStaticProps:
   - Run the function
   - Generate HTML with the data
   - Save as static file
   ↓
5. Output: .next/static/
   - Pre-rendered HTML
   - Optimized JS chunks
   - CSS files
```

## 6. The Magic: Import at Build Time

```javascript
// This actually works in Next.js!
import slidesManifest from '../../content/slides/index.json'

// At build time, webpack:
// 1. Reads the JSON file
// 2. Includes it in the bundle
// 3. No filesystem access needed in production
```

## 7. Benefits for Our Slides System

### Development
- Edit markdown files directly
- Hot reload sees changes
- No build step needed

### Production
- All slides pre-rendered as HTML
- No filesystem access needed
- Can deploy to CDN
- Works in serverless environments

### Example Build Output
```
Route (app)                          Size     First Load JS
┌ ● /slides                         312 B          87.5 kB
├ ● /slides/[id]                    178 B          94.2 kB
├   ├ /slides/genesis
├   ├ /slides/evolution
├   └ /slides/docker-journey
└ ● /slides/edit/[id]              2.1 kB         98.3 kB

● (SSG) Generated as static HTML + JSON
```

## 8. Webpack Optimizations

### Code Splitting
```javascript
// Webpack automatically splits this into separate chunk
const RevealJS = dynamic(() => import('reveal.js'), {
  loading: () => <p>Loading presentation...</p>,
  ssr: false  // Don't render on server
})
```

### Tree Shaking
```javascript
// If you only use `parse` from this library:
import { parse } from 'markdown-library'
// Webpack removes unused exports in production
```

### Asset Optimization
```javascript
// These get optimized URLs in production:
import slideStyles from './slides.module.css'
// Becomes: /_next/static/css/abc123.css
```

## Summary

For our slides system:
1. **Development**: Read markdown files directly from filesystem
2. **Build Time**: Webpack bundles everything, Next.js pre-renders pages
3. **Production**: Serve static HTML + JS, no filesystem access needed
4. **Result**: Fast, scalable, simple to deploy

This approach gives us the best of both worlds:
- Easy content editing (just markdown files)
- Blazing fast production performance (pre-rendered)
- No database complexity
- Git versioning for free