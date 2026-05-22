// LL Monitor Service Worker — handles background Web Push events

self.addEventListener("push", (event) => {
  if (!event.data) return;
  let title = "LL Monitor";
  let body = "";
  let removedWatch = null;
  try {
    const payload = event.data.json();
    title = payload.title || title;
    body = payload.body || body;
    removedWatch = payload.removed_watch || null;
  } catch {
    body = event.data.text();
  }

  event.waitUntil(
    clients.matchAll({ type: "window", includeUncontrolled: true }).then((list) => {
      // Forward removed_watch to any open app windows so they can update UI
      if (removedWatch) {
        list.forEach((c) => c.postMessage({ type: "WATCH_REMOVED", rideKey: removedWatch }));
      }
      const appVisible = list.some((c) => c.visibilityState === "visible");
      if (appVisible) return;
      return self.registration.showNotification(title, {
        body,
        icon: "/favicon.ico",
        badge: "/favicon.ico",
        tag: title,
        renotify: true,
      });
    })
  );
});

self.addEventListener("notificationclick", (event) => {
  event.notification.close();
  event.waitUntil(
    clients
      .matchAll({ type: "window", includeUncontrolled: true })
      .then((list) => {
        for (const client of list) {
          if (client.url.includes(self.location.origin) && "focus" in client) {
            return client.focus();
          }
        }
        if (clients.openWindow) return clients.openWindow("/#ll");
      })
  );
});
