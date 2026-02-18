#!/usr/bin/env node
/**
 * Build MkDocs static HTML and copy to public/docs/
 *
 * This script runs automatically before `npm run build` to ensure
 * the latest documentation is always bundled with the app.
 */

import { execSync } from 'child_process'
import { existsSync, rmSync, cpSync, mkdirSync } from 'fs'
import { join, dirname } from 'path'
import { fileURLToPath } from 'url'

const __dirname = dirname(fileURLToPath(import.meta.url))
const rootDir = join(__dirname, '..', '..')
const siteDir = join(rootDir, 'site')
const publicDocsDir = join(__dirname, '..', 'public', 'docs')

console.log('[1/3] Building MkDocs static site...')
try {
  // Try to use mkdocs from PATH first, fallback to python -m mkdocs
  try {
    execSync('mkdocs build --clean', { cwd: rootDir, stdio: 'inherit' })
  } catch (err) {
    console.log('   mkdocs not in PATH, trying python -m mkdocs...')
    execSync('python -m mkdocs build --clean', { cwd: rootDir, stdio: 'inherit' })
  }
} catch (error) {
  console.error('ERROR: MkDocs build failed!')
  console.error('Make sure mkdocs and mkdocs-material are installed:')
  console.error('  pip install mkdocs mkdocs-material')
  process.exit(1)
}

console.log('[2/3] Copying to frontend/public/docs...')
try {
  // Remove old docs if exist
  if (existsSync(publicDocsDir)) {
    rmSync(publicDocsDir, { recursive: true, force: true })
  }

  // Create parent directory if needed
  const publicDir = join(__dirname, '..', 'public')
  if (!existsSync(publicDir)) {
    mkdirSync(publicDir, { recursive: true })
  }

  // Copy site/ to public/docs/
  cpSync(siteDir, publicDocsDir, { recursive: true })
} catch (error) {
  console.error('ERROR: Failed to copy docs to public folder!')
  console.error(error.message)
  process.exit(1)
}

console.log('[3/3] Cleaning up build artifacts...')
try {
  if (existsSync(siteDir)) {
    rmSync(siteDir, { recursive: true, force: true })
  }
} catch (error) {
  console.warn('Warning: Failed to clean up site/ directory')
}

console.log('')
console.log('✅ Documentation built and copied successfully!')
console.log('   Location: frontend/public/docs/index.html')
console.log('   Accessible in app at: /docs/index.html')
console.log('')
