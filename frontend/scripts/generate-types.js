#!/usr/bin/env node
/**
 * Type generation script that generates TypeScript types from OpenAPI specs
 * Fails with clear error messages if OpenAPI specs are missing
 */

const fs = require('fs');
const path = require('path');
const { execSync } = require('child_process');

const SPEC_PATHS = {
  api: '../api/openapi.yaml',
  storage: '../storage_service/openapi.yaml',
  // executor: '../executor-service/openapi.yaml' // Deprecated - executor-service removed
};

const OUTPUT_PATHS = {
  api: './types/generated/api.ts',
  storage: './types/generated/storage.ts',
  // executor: './types/generated/executor.ts' // Deprecated - executor-service removed
};

// No fallback types - fail clearly if OpenAPI specs are missing
// This ensures we don't maintain duplicate type definitions that get out of sync

function ensureDirectoryExists(filePath) {
  const dir = path.dirname(filePath);
  if (!fs.existsSync(dir)) {
    fs.mkdirSync(dir, { recursive: true });
  }
}

function generateTypes(service, specPath, outputPath) {
  const absoluteSpecPath = path.resolve(specPath);
  const absoluteOutputPath = path.resolve(outputPath);

  if (!fs.existsSync(absoluteSpecPath)) {
    console.error(`❌ OpenAPI spec not found for ${service}: ${specPath}`);
    console.error(`   This is required for type generation.`);
    console.error(`   `);
    console.error(`   To fix this:`);
    console.error(`   1. Ensure the service is running`);
    console.error(`   2. Generate the OpenAPI spec:`);
    console.error(`      cd .. && ./scripts/generate-all-openapi-specs.sh`);
    console.error(`   3. Try building again`);
    console.error(`   `);
    return false;
  }

  console.log(`✅ Generating types for ${service} from ${specPath}`);
  try {
    ensureDirectoryExists(absoluteOutputPath);
    execSync(`npx openapi-typescript ${absoluteSpecPath} -o ${absoluteOutputPath}`, {
      stdio: 'inherit'
    });
    return true;
  } catch (error) {
    console.error(`❌ Failed to generate types for ${service}:`, error.message);
    console.error(`   OpenAPI spec exists but type generation failed.`);
    console.error(`   This usually means the spec is invalid or openapi-typescript had an error.`);
    return false;
  }
}

function main() {
  console.log('🔧 Safe type generation starting...\n');
  
  let allSuccessful = true;
  let successCount = 0;
  const services = Object.keys(SPEC_PATHS);

  for (const service of services) {
    const success = generateTypes(
      service,
      SPEC_PATHS[service],
      OUTPUT_PATHS[service]
    );
    if (success) {
      successCount++;
    } else {
      allSuccessful = false;
    }
  }

  console.log(`\n📊 Type generation complete: ${successCount}/${services.length} services successful`);

  if (!allSuccessful) {
    console.error('\n❌ Type generation failed!');
    console.error('\nOpenAPI specifications are required for building the frontend.');
    console.error('These specs define the API contracts between services.');
    console.error('\nTo fix this issue:');
    console.error('\n1. If running locally:');
    console.error('   cd .. && ./scripts/generate-all-openapi-specs.sh');
    console.error('\n2. If in CI/CD:');
    console.error('   - Check that the generate-openapi-spec workflow ran successfully');
    console.error('   - Ensure OpenAPI spec artifacts were properly downloaded');
    console.error('\n3. For manual generation per service:');
    console.error('   cd .. && docker-compose run --rm api python api/scripts/export-openapi-spec.py');
    console.error('   cd .. && docker-compose run --rm storage-service python storage_service/scripts/export-openapi-spec.py');
    console.error('   cd .. && docker-compose run --rm executor-service python executor-service/scripts/export-openapi-spec.py');
    console.error('');
    
    // Exit with failure - don't allow build to continue without types
    process.exit(1);
  }

  // All specs generated successfully
  process.exit(0);
}

if (require.main === module) {
  main();
}