# Wiki Auto-Link Configuration

This configuration defines which terms should be automatically converted to wiki links.

## Auto-Link Rules

### Always Link (Tier 1)
These terms should always be converted to wiki links when found in text:

```javascript
const ALWAYS_LINK = [
  // Platform
  'Crucible',
  'METR',
  
  // Container & Security
  'Docker',
  'Kubernetes',
  'K8s',
  'gVisor',
  'runsc',
  'Container Isolation',
  
  // Cloud
  'AWS',
  'EC2',
  
  // Frameworks
  'FastAPI',
  'Next.js',
  'TypeScript'
];
```

### Context-Aware Linking (Tier 2)
These terms should be linked based on context (not in code blocks, not if already linked):

```javascript
const CONTEXT_LINK = [
  // Services
  'Evaluation',
  'Evaluator',
  'Executor Service',
  'Monitoring Service',
  'Storage Service',
  
  // Concepts
  'Microservices',
  'Security',
  'Threat Model',
  'Adversarial Testing',
  
  // Technologies
  'Redis',
  'Python',
  'React',
  'Terraform',
  'OpenTofu'
];
```

### Special Cases
Terms that need special handling:

```javascript
const SPECIAL_CASES = {
  // Abbreviations that map to full names
  'K8s': 'Kubernetes',
  'IAM': 'AWS IAM',
  'EC2': 'AWS EC2',
  'S3': 'AWS S3',
  
  // Variations that map to canonical form
  'Container isolation': 'Container Isolation',
  'container isolation': 'Container Isolation',
  'threat model': 'Threat Model',
  'AI safety': 'AI Safety'
};
```

## Implementation Example

```typescript
function autoLinkContent(content: string, existingDocs: Set<string>): string {
  let processed = content;
  
  // Skip code blocks
  const codeBlocks: string[] = [];
  processed = processed.replace(/```[\s\S]*?```/g, (match) => {
    codeBlocks.push(match);
    return `__CODE_BLOCK_${codeBlocks.length - 1}__`;
  });
  
  // Skip already linked content
  processed = processed.replace(/\[\[[\s\S]*?\]\]/g, (match) => {
    return match; // Keep existing wiki links
  });
  
  // Apply auto-linking
  ALWAYS_LINK.forEach(term => {
    const regex = new RegExp(`\\b(${term})\\b(?!\\]\\])`, 'g');
    processed = processed.replace(regex, '[[$1]]');
  });
  
  // Restore code blocks
  codeBlocks.forEach((block, index) => {
    processed = processed.replace(`__CODE_BLOCK_${index}__`, block);
  });
  
  return processed;
}
```

## Configuration Options

```typescript
interface AutoLinkConfig {
  enabled: boolean;
  tiers: {
    always: string[];
    contextual: string[];
    never: string[];  // Terms to never auto-link
  };
  options: {
    caseInsensitive: boolean;
    wholeWordsOnly: boolean;
    skipCodeBlocks: boolean;
    skipUrls: boolean;
    skipExistingLinks: boolean;
    maxLinksPerTerm: number;  // Limit links per page
  };
}

const defaultConfig: AutoLinkConfig = {
  enabled: true,
  tiers: {
    always: ALWAYS_LINK,
    contextual: CONTEXT_LINK,
    never: ['the', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for']
  },
  options: {
    caseInsensitive: false,
    wholeWordsOnly: true,
    skipCodeBlocks: true,
    skipUrls: true,
    skipExistingLinks: true,
    maxLinksPerTerm: 3
  }
};
```

## Usage Notes

1. **Performance**: Auto-linking happens at build time, not runtime
2. **Precedence**: Manual wiki links always take precedence
3. **Updates**: Changes require rebuild to take effect
4. **Testing**: Always preview auto-linked content before publishing