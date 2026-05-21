// LL Monitor Service Worker — handles background Web Push events

self.addEventListener("push", (event) => {
  if (!event.data) return;
  let title = "LL Monitor";
  let body = "";
  try {
    const payload = event.data.json();
    title = payload.title || title;
    body = payload.body || body;
  } catch {
    body = event.data.text();
  }

  event.waitUntil(
    // If the app is open and visible, skip the system notification —
    // the SSE stream fires in-app notifications directly.
    clients.matchAll({ type: "window", includeUncontrolled: true }).then((list) => {
      const appVisible = list.some((c) => c.visibilityState === "visible");
      if (appVisible) return;
      return self.registration.showNotification(title, {
        body,
        icon: "/favicon.ico",
        badge: "/favicon.ico",
        tag: title,
        renotify: false,
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
