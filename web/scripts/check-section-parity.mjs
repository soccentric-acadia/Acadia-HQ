#!/usr/bin/env node
// Task 008 validation helper — diffs the HQ device section registry against
// the live Acadia-Configuration registry when the sibling repository is
// present. Exits non-zero on any mismatch. Run from the web/ directory:
//   node scripts/check-section-parity.mjs [path-to-Acadia-Configuration]
import { readFileSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'

const here = dirname(fileURLToPath(import.meta.url))
const webRoot = join(here, '..')
const fallback = join(webRoot, '..', '..', 'Acadia-Configuration')
const configRepo = process.argv[2] ?? fallback
const registryPath = join(configRepo, 'frontend', 'pages', 'registry.js')

let source
try {
  source = readFileSync(registryPath, 'utf8')
} catch {
  console.error(`[section-parity] cannot read ${registryPath} — pass the repo path as argv[2]`)
  process.exit(2)
}

// Parse the WebConfig NAV entries (id, label, category, adminOnly).
const entryRe = /\{\s*id:\s*'([^']+)'\s*,\s*label:\s*'([^']+)'.*?category:\s*'([^']+)'(.*?)\}/gs
const webconfig = [...source.matchAll(entryRe)].map((m) => ({
  id: m[1],
  label: m[2],
  category: m[3],
  adminOnly: /adminOnly:\s*true/.test(m[4]),
}))

// Parse the HQ registry from TypeScript source (deviceSections.ts).
const hqSource = readFileSync(join(webRoot, 'src', 'lib', 'deviceSections.ts'), 'utf8')
const hqRe = /\{\s*id:\s*'([^']+)'\s*,\s*label:\s*'([^']+)'\s*,\s*icon:\s*\w+\s*,\s*category:\s*'([^']+)'(.*?)\}/gs
const hq = [...hqSource.matchAll(hqRe)].map((m) => ({
  id: m[1],
  label: m[2],
  category: m[3],
  adminOnly: /adminOnly:\s*true/.test(m[4]),
}))

const problems = []
if (webconfig.length !== hq.length) {
  problems.push(`count mismatch: WebConfig ${webconfig.length} vs HQ ${hq.length}`)
}
for (let i = 0; i < Math.max(webconfig.length, hq.length); i++) {
  const w = webconfig[i]
  const h = hq[i]
  if (!w || !h) {
    problems.push(`missing entry at index ${i}: webconfig=${w?.id ?? '—'} hq=${h?.id ?? '—'}`)
    continue
  }
  if (w.id !== h.id) problems.push(`order mismatch at ${i}: ${w.id} vs ${h.id}`)
  if (w.label !== h.label) problems.push(`label mismatch ${w.id}: '${w.label}' vs '${h.label}'`)
  if (w.category !== h.category) problems.push(`category mismatch ${w.id}: ${w.category} vs ${h.category}`)
  if (w.adminOnly !== h.adminOnly) problems.push(`adminOnly mismatch ${w.id}: ${w.adminOnly} vs ${h.adminOnly}`)
}

if (problems.length) {
  console.error('[section-parity] FAILED:\n  ' + problems.join('\n  '))
  process.exit(1)
}
console.log(`[section-parity] OK — ${hq.length}/${webconfig.length} sections match WebConfig registry (ids, labels, categories, adminOnly, order)`)