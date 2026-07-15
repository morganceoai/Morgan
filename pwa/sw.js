const CACHE = 'morgan-pwa-v4';
const OFFLINE_URLS = ['/pwa/', '/pwa/index.html'];

self.addEventListener('install', e => {
  e.waitUntil(
    caches.open(CACHE)
      .then(c => c.addAll(OFFLINE_URLS))
      .then(() => self.skipWaiting())
  );
});

self.addEventListener('activate', e => {
  e.waitUntil(
    caches.keys()
      .then(keys => Promise.all(keys.filter(k => k !== CACHE).map(k => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', e => {
  if (e.request.url.includes('/api/')) return;
  e.respondWith(fetch(e.request).catch(() => caches.match(e.request)));
});

self.addEventListener('push', e => {
  const data = e.data ? e.data.json() : {};
  const title = data.title || 'Morgan';
  const options = {
    body:    data.body  || '',
    icon:    '/pwa/icon-192.png',
    badge:   '/pwa/icon-192.png',
    vibrate: [200, 100, 200],
    tag:     'morgan-notification',
    renotify: true,
    data:    { url: data.url || '/pwa/' },
  };
  e.waitUntil(self.registration.showNotification(title, options));
});

self.addEventListener('notificationclick', e => {
  e.notification.close();
  e.waitUntil(
    clients.matchAll({ type: 'window', includeUncontrolled: true }).then(list => {
      for (const c of list) {
        if (c.url.includes('/pwa/') && 'focus' in c) return c.focus();
      }
      return clients.openWindow(e.notification.data.url);
    })
  );
});
