const fs = require('node:fs')
const path = require('node:path')

const coveragePath = path.resolve(__dirname, '..', 'coverage', 'coverage-final.json')
const diagnosticsPath = path.resolve(__dirname, '..', 'coverage', 'coverage-diagnostics.json')

if (!fs.existsSync(coveragePath)) {
  console.error('[coverage] Missing coverage-final.json')
  process.exit(1)
}

const report = JSON.parse(fs.readFileSync(coveragePath, 'utf8'))
let totalStatements = 0
let executedStatements = 0
let filesWithMetaSeen = 0

for (const fileData of Object.values(report)) {
  const statements = Object.values(fileData?.s || {})
  totalStatements += statements.length
  executedStatements += statements.filter((count) => count > 0).length
  if (fileData?.meta?.seen && Object.keys(fileData.meta.seen).length > 0) {
    filesWithMetaSeen += 1
  }
}

const summary = {
  totalStatements,
  executedStatements,
  files: Object.keys(report).length,
  filesWithMetaSeen,
}

fs.writeFileSync(diagnosticsPath, JSON.stringify(summary, null, 2))

if (totalStatements === 0 || executedStatements === 0) {
  console.error(
    '[coverage] Invalid coverage report: 0 executed statements detected. ' +
      'Vitest v8 coverage is currently unreliable in this environment. ' +
      'See coverage/coverage-diagnostics.json for details.'
  )
  process.exit(1)
}

const pct = ((executedStatements / totalStatements) * 100).toFixed(2)
console.log(`[coverage] Executed statements: ${executedStatements}/${totalStatements} (${pct}%)`)
