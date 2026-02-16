/**
 * Yahtzee PWA Service Worker — cache static assets for offline use.
 *
 * Strategy: stale-while-revalidate for static assets (serves cached version
 * immediately, fetches fresh copy in background to update cache for next load).
 * Network-first for everything else (HTML pages, WebSocket, API calls).
 */

const CACHE_NAME = "yahtzee-v2";
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

    // Stale-while-revalidate for static assets: serve cached version
    // immediately, fetch fresh copy in background to update cache.
    if (url.pathname.startsWith("/static/")) {
        event.respondWith(
            caches.open(CACHE_NAME).then((cache) =>
                cache.match(event.request).then((cached) => {
                    const fetched = fetch(event.request).then((response) => {
                        cache.put(event.request, response.clone());
                        return response;
                    });
                    return cached || fetched;
                })
            )
        );
        return;
    }

    // Network-first for everything else
    event.respondWith(
        fetch(event.request).catch(() => caches.match(event.request))
    );
});
