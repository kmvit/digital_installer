import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { VitePWA } from "vite-plugin-pwa";

export default defineConfig({
  plugins: [
    react(),
    VitePWA({
      registerType: "autoUpdate",
      includeAssets: ["icon-192.svg", "icon-512.svg"],

      manifest: {
        name: "СВ ФИНАМ — Цифровой монтажник",
        short_name: "СВ ФИНАМ",
        description: "Управление бригадами и монтажными работами",
        theme_color: "#1565c0",
        background_color: "#f5f5f5",
        display: "standalone",
        orientation: "portrait",
        start_url: "/",
        scope: "/",
        icons: [
          {
            src: "icon-192.svg",
            sizes: "192x192",
            type: "image/svg+xml",
            purpose: "any maskable",
          },
          {
            src: "icon-512.svg",
            sizes: "512x512",
            type: "image/svg+xml",
            purpose: "any maskable",
          },
        ],
      },

      workbox: {
        // Макс. размер кэшируемого файла — 5 МБ
        maximumFileSizeToCacheInBytes: 5 * 1024 * 1024,

        // Precache — статика (JS, CSS, HTML)
        globPatterns: ["**/*.{js,css,html,svg,png,ico,woff2}"],

        // Runtime caching
        runtimeCaching: [
          // API: Network First (пробуем сеть, fallback на кэш)
          {
            urlPattern: /^https?:\/\/.*\/api\//,
            handler: "NetworkFirst",
            options: {
              cacheName: "api-cache",
              expiration: {
                maxEntries: 200,
                maxAgeSeconds: 60 * 60 * 24, // 1 день
              },
              cacheableResponse: {
                statuses: [0, 200],
              },
              networkTimeoutSeconds: 5,
            },
          },
          // Медиа/фото: Cache First
          {
            urlPattern: /^https?:\/\/.*\/media\//,
            handler: "CacheFirst",
            options: {
              cacheName: "media-cache",
              expiration: {
                maxEntries: 100,
                maxAgeSeconds: 60 * 60 * 24 * 7, // 7 дней
              },
              cacheableResponse: {
                statuses: [0, 200],
              },
            },
          },
          // OSM тайлы карты: Cache First
          {
            urlPattern: /^https:\/\/.*tile\.openstreetmap\.org\//,
            handler: "CacheFirst",
            options: {
              cacheName: "map-tiles",
              expiration: {
                maxEntries: 500,
                maxAgeSeconds: 60 * 60 * 24 * 30, // 30 дней
              },
              cacheableResponse: {
                statuses: [0, 200],
              },
            },
          },
        ],

        // Навигация — всегда отдаём index.html (SPA)
        navigateFallback: "/index.html",
        navigateFallbackDenylist: [/^\/api\//, /^\/admin\//, /^\/static\//, /^\/media\//],

        // Очистка устаревших кэшей
        cleanupOutdatedCaches: true,
      },
    }),
  ],
  server: {
    port: 5173,
  },
});
