import { spawn } from 'child_process';
import http from 'http';
import { readFileSync } from 'fs';
import { resolve, dirname } from 'path';
import { fileURLToPath } from 'url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const extPath = resolve(__dirname, 'dist');

console.log('====================================================');
console.log('  SignBridge Live — Automated Extension Diagnostic');
console.log('====================================================\n');

// 1. Verify dist files exist
const requiredFiles = [
  'manifest.json',
  'background.js',
  'content.js',
  'popup.html',
  'options.html',
  'assets/index.css',
];

let allExist = true;
for (const file of requiredFiles) {
  const full = resolve(extPath, file);
  try {
    readFileSync(full);
    console.log(`  ✓ Found: ${file}`);
  } catch (e) {
    console.error(`  ✗ Missing: ${file}`);
    allExist = false;
  }
}

if (!allExist) {
  console.error('\n✗ Diagnostic failed: Missing dist files. Run `npm run build` in extension/.');
  process.exit(1);
}

// 2. Validate manifest.json syntax & options
try {
  const manifest = JSON.parse(readFileSync(resolve(extPath, 'manifest.json'), 'utf-8'));
  console.log(`\n  ✓ Manifest Version: ${manifest.manifest_version}`);
  console.log(`  ✓ Extension Name: ${manifest.name} v${manifest.version}`);
  console.log(`  ✓ Background Service Worker: ${manifest.background.service_worker}`);
  console.log(`  ✓ Content Script Matches: ${manifest.content_scripts[0].matches.join(', ')}`);
  console.log(`  ✓ Default Popup: ${manifest.action.default_popup}`);
  console.log(`  ✓ Options Page: ${manifest.options_page}`);
} catch (e) {
  console.error('\n✗ Invalid manifest.json:', e);
  process.exit(1);
}

console.log('\n====================================================');
console.log('  ✅ Extension static bundle verification PASSED!');
console.log('====================================================');
