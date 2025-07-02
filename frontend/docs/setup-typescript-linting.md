# Setting Up TypeScript Linting to Catch Errors Early

## The Problem

Currently, TypeScript errors like "Object is possibly 'undefined'" are only caught during the build phase (`npm run build`), not during linting. This means developers have to wait for a full build to see these errors.

## Solution: Configure ESLint with TypeScript

To catch these errors during linting, you need to set up ESLint with TypeScript parser and rules.

### 1. Install Required Packages

```bash
npm install --save-dev @typescript-eslint/parser @typescript-eslint/eslint-plugin
```

### 2. Update ESLint Configuration

Create or update `.eslintrc.json`:

```json
{
  "extends": [
    "next/core-web-vitals",
    "plugin:@typescript-eslint/recommended",
    "plugin:@typescript-eslint/recommended-requiring-type-checking"
  ],
  "parser": "@typescript-eslint/parser",
  "parserOptions": {
    "project": "./tsconfig.json",
    "tsconfigRootDir": "."
  },
  "plugins": ["@typescript-eslint"],
  "rules": {
    // Catch the same errors as TypeScript compiler
    "@typescript-eslint/no-unsafe-assignment": "error",
    "@typescript-eslint/no-unsafe-member-access": "error",
    "@typescript-eslint/no-unsafe-call": "error",
    "@typescript-eslint/no-unsafe-return": "error",
    "@typescript-eslint/no-unused-vars": [
      "error",
      {
        "argsIgnorePattern": "^_",
        "varsIgnorePattern": "^_"
      }
    ],

    // Match tsconfig.json strictness
    "@typescript-eslint/strict-boolean-expressions": "error",
    "@typescript-eslint/no-unnecessary-condition": "error",
    "@typescript-eslint/no-unsafe-argument": "error"
  },
  "overrides": [
    {
      "files": ["*.ts", "*.tsx"],
      "rules": {
        // TypeScript-specific rules
      }
    }
  ]
}
```

### 3. Add Lint Script

Update `package.json`:

```json
{
  "scripts": {
    "lint": "next lint",
    "lint:fix": "next lint --fix",
    "type-check": "tsc --noEmit",
    "lint:all": "npm run lint && npm run type-check"
  }
}
```

### 4. VS Code Integration

For real-time error detection in VS Code, create `.vscode/settings.json`:

```json
{
  "eslint.validate": ["javascript", "javascriptreact", "typescript", "typescriptreact"],
  "typescript.tsdk": "node_modules/typescript/lib",
  "editor.codeActionsOnSave": {
    "source.fixAll.eslint": true
  }
}
```

## Benefits

1. **Catch errors during development** - See TypeScript errors immediately in your editor
2. **Faster feedback loop** - No need to run full build to see type errors
3. **Consistent with build** - Same errors caught by linter and compiler
4. **CI/CD friendly** - Can run `npm run lint:all` in CI pipeline

## Common TypeScript Errors That Will Be Caught

- Object is possibly 'undefined'
- Unused variables and imports
- Missing return statements
- Type mismatches
- Null/undefined access

## Example Workflow

```bash
# During development
npm run lint:all      # Run both ESLint and TypeScript checks

# Before commit
npm run lint:fix      # Auto-fix what can be fixed
npm run type-check    # Final type check

# In CI/CD
npm run lint:all && npm run build
```

## Additional Tools

### 1. Pre-commit Hooks

Use `husky` and `lint-staged` to run checks before commits:

```bash
npm install --save-dev husky lint-staged
```

Add to `package.json`:

```json
{
  "lint-staged": {
    "*.{ts,tsx}": ["eslint --fix", "bash -c 'tsc --noEmit'"]
  }
}
```

### 2. Watch Mode

For continuous type checking during development:

```bash
# In a separate terminal
tsc --watch --noEmit
```

This setup ensures TypeScript errors are caught early and consistently throughout the development process.
