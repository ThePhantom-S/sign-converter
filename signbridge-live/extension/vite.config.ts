import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import { resolve } from 'path';
import { writeFileSync, mkdirSync, cpSync, existsSync, readFileSync } from 'fs';

// Post-build plugin: moves HTML files to dist root and creates icon placeholders
function extensionBuildPlugin() {
  return {
    name: 'extension-build-plugin',
    closeBundle() {
      const distDir = resolve(__dirname, 'dist');

      // Move popup.html and options.html to dist root (manifest references them there)
      try {
        const popupSrc = resolve(distDir, 'src/popup/index.html');
        const optionsSrc = resolve(distDir, 'src/options/index.html');

        if (existsSync(popupSrc)) {
          let html = readFileSync(popupSrc, 'utf-8');
          // Fix both relative (../../assets/) and absolute (/assets/) paths
          html = html.replace(/\.\.\/\.\.\/assets\//g, 'assets/');
          html = html.replace(/src="\/assets\//g, 'src="assets/');
          html = html.replace(/href="\/assets\//g, 'href="assets/');
          writeFileSync(resolve(distDir, 'popup.html'), html);
          console.log('[ext-plugin] ✓ popup.html → dist/popup.html');
        }

        if (existsSync(optionsSrc)) {
          let html = readFileSync(optionsSrc, 'utf-8');
          html = html.replace(/\.\.\/\.\.\/assets\//g, 'assets/');
          html = html.replace(/src="\/assets\//g, 'src="assets/');
          html = html.replace(/href="\/assets\//g, 'href="assets/');
          writeFileSync(resolve(distDir, 'options.html'), html);
          console.log('[ext-plugin] ✓ options.html → dist/options.html');
        }
      } catch (e) {
        console.error('[ext-plugin] HTML copy failed:', e);
      }

      // Create icon placeholders if no real icons exist
      try {
        mkdirSync(resolve(distDir, 'icons'), { recursive: true });
        try {
          cpSync(resolve(__dirname, 'public/icons'), resolve(distDir, 'icons'), { recursive: true });
        } catch {
          // Minimal 1×1 transparent PNG as placeholder so Chrome doesn't complain
          const png1x1 = Buffer.from(
            '89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c489' +
            '0000000a49444154789c6260000000020001e221bc330000000049454e44ae426082',
            'hex'
          );
          for (const name of ['icon16.png', 'icon32.png', 'icon48.png', 'icon128.png']) {
            writeFileSync(resolve(distDir, 'icons', name), png1x1);
          }
        }
      } catch (e) {
        console.warn('[ext-plugin] Icon setup warning:', e);
      }
    },
  };
}

export default defineConfig({
  plugins: [react(), extensionBuildPlugin()],
  resolve: {
    alias: { '@': resolve(__dirname, './src') },
  },
  build: {
    outDir: 'dist',
    emptyOutDir: true,
    minify: false,
    rollupOptions: {
      input: {
        popup: resolve(__dirname, 'src/popup/index.html'),
        options: resolve(__dirname, 'src/options/index.html'),
        background: resolve(__dirname, 'src/background/index.ts'),
        content: resolve(__dirname, 'src/content/index.ts'),
      },
      output: {
        // background.js and content.js must be at dist root
        entryFileNames: (chunk) => {
          if (chunk.name === 'background' || chunk.name === 'content') {
            return '[name].js';
          }
          return 'assets/[name]-[hash].js';
        },
        chunkFileNames: 'assets/[name]-[hash].js',
        // Use a stable CSS filename so content.js can find it without a hash
        assetFileNames: (asset) => {
          if (asset.name?.endsWith('.css')) return 'assets/index.css';
          return 'assets/[name]-[hash].[ext]';
        },
      },
    },
  },
});
