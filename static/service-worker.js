/**
 * Yahtzee PWA Service Worker — cache static assets for offline use.
 *
 * Strategy: cache-first for static assets (CSS/JS/icons), network-first
 * for everything else (HTML pages, WebSocket, API calls).
 */

const CACHE_NAME = "yahtzee-v1";
const STATIC_ASSETS = [
    "/static/style.css",
    "/static/dice.css",
    "/static/game.js",
    "/static/icon-192.png",
    "/static/icon-512.png",
];

self.addEventListener("install", (event) => {
    event.waitUntil(
        caches.open(CACHE_NAME).then((cache) => cache.addAll(STATIC_ASSETS))
    );
    self.skipWaiting();
});

self.addEventListener("activate", (event) => {
    event.waitUntil(
        caches.keys().then((keys) =>
            Promise.all(keys.filter((k) => k !== CACHE_NAME).map((k) => caches.delete(k)))
        )
    );
    self.clients.claim();
});

self.addEventListener("fetch", (event) => {
    const url = new URL(event.request.url);

    // Only cache-first for static assets
    if (url.pathname.startsWith("/static/")) {
        event.respondWith(
            caches.match(event.request).then((cached) => cached || fetch(event.request))
        );
        return;
    }

    // Network-first for everything else
    event.respondWith(
        fetch(event.request).catch(() => caches.match(event.request))
    );
});
