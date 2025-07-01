#!/usr/bin/env node

/**
 * Script to analyze wiki links in documentation
 * Generates a report of missing links and orphaned documents
 */

const { execSync } = require('child_process');
const path = require('path');
const fs = require('fs');

console.log('🔍 Wiki Links Analyzer\n');

// Check if we're in the frontend directory
if (!fs.existsSync('package.json') || !fs.existsSync('lib/wiki')) {
  console.error('❌ Error: This script must be run from the frontend directory');
  process.exit(1);
}

// Compile TypeScript files if needed
console.log('📦 Compiling TypeScript files...');
try {
  execSync('npx tsc lib/wiki/analyze-missing-links.ts --module commonjs --target es2020 --esModuleInterop --resolveJsonModule', {
    stdio: 'inherit'
  });
} catch (error) {
  console.error('❌ Error compiling TypeScript:', error.message);
  process.exit(1);
}

// Run the analyzer
console.log('\n🚀 Running wiki link analysis...\n');
try {
  execSync('node lib/wiki/analyze-missing-links.js', {
    stdio: 'inherit'
  });
} catch (error) {
  console.error('❌ Error running analyzer:', error.message);
  process.exit(1);
}

console.log('\n✨ Done!');