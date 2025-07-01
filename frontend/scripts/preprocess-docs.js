const fs = require('fs');
const path = require('path');
const matter = require('gray-matter');
const crypto = require('crypto');

const docsDir = './docs';
const cacheDir = './.docs-cache';

// Create cache directory
if (!fs.existsSync(cacheDir)) {
  fs.mkdirSync(cacheDir, { recursive: true });
}

// Process all markdown files
function processMarkdownFiles(dir) {
  const files = fs.readdirSync(dir);
  const processed = {};
  
  files.forEach(file => {
    const filePath = path.join(dir, file);
    const stat = fs.statSync(filePath);
    
    if (stat.isDirectory()) {
      Object.assign(processed, processMarkdownFiles(filePath));
    } else if (file.endsWith('.md') || file.endsWith('.mdx')) {
      const content = fs.readFileSync(filePath, 'utf8');
      const { data, content: body } = matter(content);
      
      // Generate hash for caching
      const hash = crypto.createHash('md5').update(content).digest('hex');
      
      // Store processed data
      const relativePath = path.relative(docsDir, filePath);
      processed[relativePath] = {
        frontmatter: data,
        content: body,
        hash: hash,
        path: relativePath
      };
    }
  });
  
  return processed;
}

console.log('Preprocessing documentation files...');
const startTime = Date.now();

const processedDocs = processMarkdownFiles(docsDir);
fs.writeFileSync(
  path.join(cacheDir, 'processed-docs.json'),
  JSON.stringify(processedDocs, null, 2)
);

const endTime = Date.now();
console.log(`Preprocessed ${Object.keys(processedDocs).length} docs in ${endTime - startTime}ms`);