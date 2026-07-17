import { build } from 'vite';
import react from '@vitejs/plugin-react';
import { resolve, dirname } from 'path';
import { fileURLToPath } from 'url';

const __dirname = dirname(fileURLToPath(import.meta.url));

async function runBuild() {
  console.log('--- 1. Building Popup & Options (Standard UI Pages) ---');
  await build({
    configFile: false,
    plugins: [react()],
    resolve: {
      alias: {
        '@': resolve(__dirname, './src'),
      },
    },
    build: {
      outDir: 'dist',
      emptyOutDir: true,
      minify: false,
      rollupOptions: {
        input: {
          popup: resolve(__dirname, 'src/popup/index.html'),
          options: resolve(__dirname, 'src/options/index.html'),
        },
      },
    },
  });

  console.log('\n--- 2. Building Content Script (IIFE Library Mode) ---');
  await build({
    configFile: false,
    plugins: [react()],
    resolve: {
      alias: {
        '@': resolve(__dirname, './src'),
      },
    },
    build: {
      outDir: 'dist',
      emptyOutDir: false,
      minify: false,
      lib: {
        entry: resolve(__dirname, 'src/content/index.ts'),
        name: 'content',
        fileName: () => 'content.js',
        formats: ['iife'],
      },
    },
  });

  console.log('\n--- 3. Building Background Service Worker (IIFE Library Mode) ---');
  await build({
    configFile: false,
    plugins: [react()],
    resolve: {
      alias: {
        '@': resolve(__dirname, './src'),
      },
    },
    build: {
      outDir: 'dist',
      emptyOutDir: false,
      minify: false,
      lib: {
        entry: resolve(__dirname, 'src/background/index.ts'),
        name: 'background',
        fileName: () => 'background.js',
        formats: ['iife'],
      },
    },
  });

  console.log('\nBuild complete! All scripts successfully generated inside /dist');
}

runBuild().catch((err) => {
  console.error('Build failed:', err);
  process.exit(1);
});
