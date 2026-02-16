// @ts-check
import { defineConfig } from 'astro/config';
import react from '@astrojs/react';

// https://astro.build/config
export default defineConfig({
  integrations: [react()],
  base: '/tools/land-parcel-automater',
  trailingSlash: 'ignore',
  build: {
    assets: '_astro'
  },
  vite: {
    assetsInclude: ['**/*.geojson'],
    json: {
      stringify: false
    },
    base: '/tools/land-parcel-automater/'
  }
});
