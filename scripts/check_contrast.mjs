#!/usr/bin/env node
/**
 * Design Tokens Contrast Regression Check
 *
 * Parses tokens.css and verifies that foreground/background color pairs
 * meet WCAG 2.1 AA minimum contrast ratios (4.5:1 for normal text,
 * 3:1 for large text / UI components).
 *
 * Usage:
 *   node scripts/check_contrast.mjs
 *
 * Exit codes:
 *   0 = all checks pass
 *   1 = one or more contrast failures
 */

import { readFileSync } from 'fs';
import { resolve, dirname } from 'path';
import { fileURLToPath } from 'url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const TOKENS_PATH = resolve(__dirname, '../frontend/src/assets/design-system/tokens.css');

// ---------------------------------------------------------------------------
// Color math (sRGB relative luminance + WCAG contrast ratio)
// ---------------------------------------------------------------------------

/** Parse hex color (#RGB or #RRGGBB) to [r, g, b] in 0-255 */
function hexToRgb(hex) {
  hex = hex.replace('#', '');
  if (hex.length === 3) {
    hex = hex[0] + hex[0] + hex[1] + hex[1] + hex[2] + hex[2];
  }
  return [
    parseInt(hex.slice(0, 2), 16),
    parseInt(hex.slice(2, 4), 16),
    parseInt(hex.slice(4, 6), 16),
  ];
}

/** sRGB channel to linear */
function srgbToLinear(c) {
  c = c / 255;
  return c <= 0.04045 ? c / 12.92 : Math.pow((c + 0.055) / 1.055, 2.4);
}

/** Relative luminance per WCAG 2.1 */
function luminance([r, g, b]) {
  return 0.2126 * srgbToLinear(r) + 0.7152 * srgbToLinear(g) + 0.0722 * srgbToLinear(b);
}

/** WCAG contrast ratio between two hex colors */
function contrastRatio(hex1, hex2) {
  const l1 = luminance(hexToRgb(hex1));
  const l2 = luminance(hexToRgb(hex2));
  const lighter = Math.max(l1, l2);
  const darker = Math.min(l1, l2);
  return (lighter + 0.05) / (darker + 0.05);
}

// ---------------------------------------------------------------------------
// Parse tokens from CSS
// ---------------------------------------------------------------------------

function parseTokens(css) {
  const tokens = {};
  // Match lines like:  --ds-something: #RRGGBB;
  const re = /--(ds-[\w-]+)\s*:\s*(#[0-9A-Fa-f]{3,8})\s*;/g;
  let m;
  while ((m = re.exec(css)) !== null) {
    tokens[m[1]] = m[2];
  }
  return tokens;
}

// ---------------------------------------------------------------------------
// Contrast pairs to check
// ---------------------------------------------------------------------------

/**
 * Each entry: [foreground token, background token, minimum ratio, label]
 * 4.5 = WCAG AA normal text, 3.0 = WCAG AA large text / UI components
 */
function getCheckPairs(prefix) {
  // prefix is '' for light mode, 'dark-' for dark mode
  return [
    // Text on surfaces
    ['ds-surface-900', 'ds-surface-0', 4.5, 'Primary text on white'],
    ['ds-color-text-secondary', 'ds-surface-0', 4.5, 'Secondary text on white'],
    ['ds-surface-900', 'ds-surface-50', 4.5, 'Primary text on surface-50'],
    ['ds-surface-900', 'ds-surface-100', 4.5, 'Primary text on surface-100'],

    // Entity colors on white (used as text labels)
    ['ds-entity-character', 'ds-surface-0', 3.0, 'Entity character on white'],
    ['ds-entity-location', 'ds-surface-0', 3.0, 'Entity location on white'],
    ['ds-entity-organization', 'ds-surface-0', 3.0, 'Entity organization on white'],
    ['ds-entity-object', 'ds-surface-0', 3.0, 'Entity object on white'],
    ['ds-entity-event', 'ds-surface-0', 3.0, 'Entity event on white'],
    ['ds-entity-animal', 'ds-surface-0', 3.0, 'Entity animal on white'],
    ['ds-entity-creature', 'ds-surface-0', 3.0, 'Entity creature on white'],
    ['ds-entity-building', 'ds-surface-0', 3.0, 'Entity building on white'],
    ['ds-entity-region', 'ds-surface-0', 3.0, 'Entity region on white'],
    ['ds-entity-vehicle', 'ds-surface-0', 3.0, 'Entity vehicle on white'],
    ['ds-entity-faction', 'ds-surface-0', 3.0, 'Entity faction on white'],
    ['ds-entity-family', 'ds-surface-0', 3.0, 'Entity family on white'],
    ['ds-entity-time-period', 'ds-surface-0', 3.0, 'Entity time-period on white'],
    ['ds-entity-concept', 'ds-surface-0', 3.0, 'Entity concept on white'],
    ['ds-entity-religion', 'ds-surface-0', 3.0, 'Entity religion on white'],
    ['ds-entity-magic-system', 'ds-surface-0', 3.0, 'Entity magic-system on white'],
    ['ds-entity-work', 'ds-surface-0', 3.0, 'Entity work on white'],
    ['ds-entity-title', 'ds-surface-0', 3.0, 'Entity title on white'],
    ['ds-entity-language', 'ds-surface-0', 3.0, 'Entity language on white'],
    ['ds-entity-other', 'ds-surface-0', 3.0, 'Entity other on white'],

    // Alert severity text on alert backgrounds
    ['ds-alert-critical', 'ds-alert-critical-bg', 3.0, 'Alert critical on its bg'],
    ['ds-alert-high', 'ds-alert-high-bg', 3.0, 'Alert high on its bg'],
    ['ds-alert-medium', 'ds-alert-medium-bg', 3.0, 'Alert medium on its bg'],
    ['ds-alert-low', 'ds-alert-low-bg', 3.0, 'Alert low on its bg'],
    ['ds-alert-info', 'ds-alert-info-bg', 3.0, 'Alert info on its bg'],

    // Semantic colors on white
    ['ds-success-600', 'ds-surface-0', 3.0, 'Success-600 on white'],
    ['ds-warning-600', 'ds-surface-0', 3.0, 'Warning-600 on white'],
    ['ds-error-600', 'ds-surface-0', 3.0, 'Error-600 on white'],
    ['ds-info-600', 'ds-surface-0', 3.0, 'Info-600 on white'],

    // Primary colors
    ['ds-primary-600', 'ds-surface-0', 4.5, 'Primary-600 on white'],
    ['ds-primary-700', 'ds-surface-0', 4.5, 'Primary-700 on white'],
  ];
}

// ---------------------------------------------------------------------------
// Run checks
// ---------------------------------------------------------------------------

const css = readFileSync(TOKENS_PATH, 'utf-8');

// Split CSS into :root (light) and .dark (dark) blocks
const rootMatch = css.match(/:root\s*\{([^}]+)\}/s);
const darkMatch = css.match(/\.dark[\s\S]*?\{([\s\S]*?)\n\}/);

if (!rootMatch) {
  console.error('Could not find :root block in tokens.css');
  process.exit(1);
}

const lightTokens = parseTokens(rootMatch[1]);
const darkTokens = darkMatch ? { ...lightTokens, ...parseTokens(darkMatch[1]) } : null;

// Also parse the hardcoded text-secondary from the comment
// --ds-color-text-secondary uses #475569 as fallback
if (!lightTokens['ds-color-text-secondary']) {
  lightTokens['ds-color-text-secondary'] = '#475569';
}

let failures = 0;
let passes = 0;

function checkMode(label, tokens, pairs) {
  console.log(`\n=== ${label} ===\n`);
  for (const [fgToken, bgToken, minRatio, name] of pairs) {
    const fg = tokens[fgToken];
    const bg = tokens[bgToken];
    if (!fg || !bg) {
      // Skip pairs where tokens are not hex colors (e.g. var() references)
      continue;
    }
    const ratio = contrastRatio(fg, bg);
    const pass = ratio >= minRatio;
    const icon = pass ? 'PASS' : 'FAIL';
    const line = `  [${icon}] ${name}: ${ratio.toFixed(2)}:1 (min ${minRatio}:1) | ${fgToken}=${fg} on ${bgToken}=${bg}`;
    if (pass) {
      passes++;
    } else {
      failures++;
    }
    console.log(line);
  }
}

const lightPairs = getCheckPairs();
checkMode('Light Mode', lightTokens, lightPairs);
if (darkTokens) {
  // In dark mode, primary text uses brighter variants (400/500 instead of 600/700)
  const darkPairs = getCheckPairs().map(([fg, bg, min, name]) => {
    if (fg === 'ds-primary-600') return ['ds-primary-400', bg, min, name.replace('600', '400')];
    if (fg === 'ds-primary-700') return ['ds-primary-500', bg, min, name.replace('700', '500')];
    return [fg, bg, min, name];
  });
  checkMode('Dark Mode', darkTokens, darkPairs);
}

console.log(`\n--- Summary: ${passes} passed, ${failures} failed ---`);
if (failures > 0) {
  console.log('Contrast regression detected! Fix the failing token pairs above.');
  process.exit(1);
}
console.log('All contrast checks passed.');
