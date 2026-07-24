import { defineConfig } from 'astro/config';
import tailwindcss from '@tailwindcss/vite';

// BASE_PATH: '/' em domínio próprio; '/aikido-aggregator' no GitHub Pages de projeto
export default defineConfig({
  site: process.env.SITE_URL || 'https://serlus.github.io',
  base: process.env.BASE_PATH || '/',
  trailingSlash: 'ignore',
  vite: { plugins: [tailwindcss()] },
});
