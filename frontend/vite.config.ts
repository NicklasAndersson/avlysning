import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { VitePWA } from 'vite-plugin-pwa'

export default defineConfig({
  plugins: [
    react(),
    VitePWA({
      registerType: 'autoUpdate',
      includeAssets: ['favicon.svg'],
      workbox: {
        globPatterns: ['**/*.{js,css,html,svg,png,woff2}'],
        runtimeCaching: [
          {
            urlPattern: /\/data\/skjutfalt_status\.json$/,
            handler: 'NetworkFirst',
            options: {
              cacheName: 'status-data',
              expiration: { maxAgeSeconds: 3600 },
            },
          },
          {
            urlPattern: /\/data\/skjutfalt\.geojson$/,
            handler: 'CacheFirst',
            options: {
              cacheName: 'geojson-data',
              expiration: { maxAgeSeconds: 86400 * 7 },
            },
          },
          {
            urlPattern: /\/data\/field_config\.json$/,
            handler: 'CacheFirst',
            options: {
              cacheName: 'field-config',
              expiration: { maxAgeSeconds: 86400 * 7 },
            },
          },
          {
            urlPattern: /\/data\/sweden\.pmtiles$/,
            handler: 'CacheFirst',
            options: {
              cacheName: 'pmtiles',
              expiration: { maxAgeSeconds: 86400 * 30 },
              cacheableResponse: { statuses: [0, 200, 206] },
              rangeRequests: true,
            },
          },
          {
            urlPattern: /^https:\/\/protomaps\.github\.io\//,
            handler: 'CacheFirst',
            options: {
              cacheName: 'protomaps-assets',
              expiration: { maxAgeSeconds: 86400 * 30 },
            },
          },
        ],
      },
      manifest: {
        name: 'FM Avlysning',
        short_name: 'Avlysning',
        description: 'Aktiva avlysningar för svenska skjut- och övningsfält',
        theme_color: '#1b3a2d',
        background_color: '#f5f5f5',
        display: 'standalone',
        orientation: 'any',
        start_url: '/',
        icons: [
          {
            src: '/icon-192.png',
            sizes: '192x192',
            type: 'image/png',
          },
          {
            src: '/icon-512.png',
            sizes: '512x512',
            type: 'image/png',
          },
          {
            src: '/icon-512.png',
            sizes: '512x512',
            type: 'image/png',
            purpose: 'maskable',
          },
        ],
      },
    }),
  ],
  server: {
    port: 5173,
  },
  publicDir: 'public',
})
