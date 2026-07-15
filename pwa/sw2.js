// SW push-only — sem cache. Actualiza sempre da rede.
self.addEventListener('install', () => self.skipWaiting());

self.addEventListener('activate', e => {
  e.waitUntil(
    caches.keys()
      .then(keys => Promise.all(keys.map(k => caches.delete(k))))
      .then(() => self.clients.claim())
      .then(() => self.clients.matchAll({ type: 'window' }))
      .then(cs => cs.forEach(c => c.postMessage({ type: 'SW_UPDATED' })))
  );
});

// nunca interceptar pedidos — sempre rede directa
// (sem listener 'fetch' = comportamento padrão do browser)

self.addEventListener('push', e => {
  const data = e.data ? e.data.json() : {};
  const title = data.title || 'Morgan';
  const options = {
    body:     data.body  || '',
    icon:     '/app/icon-192.png',
    badge:    '/app/icon-192.png',
    vibrate:  [200, 100, 200],
    tag:      'morgan-notification',
    renotify: true,
    data:     { url: data.url || '/app/' },
  };
  e.waitUntil(self.registration.showNotification(title, options));
});

self.addEventListener('notificationclick', e => {
  e.notification.close();
  e.waitUntil(
    clients.matchAll({ type: 'window', includeUncontrolled: true }).then(list => {
      for (const c of list) {
        if (c.url.includes('/app/') && 'focus' in c) return c.focus();
      }
      return clients.openWindow(e.notification.data.url);
    })
  );
});
