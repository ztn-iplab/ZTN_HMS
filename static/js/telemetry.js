(() => {
  const ENDPOINT = "/auth/telemetry";
  const STORAGE_KEY = "hms_telemetry_session";
  const LABEL_KEY = "hms_telemetry_label";
  const LABEL_PROMPT_KEY = "hms_telemetry_label_prompted";
  const MAX_QUEUE = 50;
  const FLUSH_INTERVAL_MS = 5000;
  const SCROLL_THROTTLE_MS = 800;

  const state = {
    sessionId: "",
    sessionLabel: "",
    queue: [],
    lastFlush: Date.now(),
    pageStart: Date.now(),
    lastActivity: Date.now(),
    inputCache: new Map(),
    maxScrollPct: 0,
    lastScrollEmit: 0,
    clickCount: 0,
    inputCount: 0,
    keyCount: 0,
    idleMs: 0,
    lastIdleCheck: Date.now(),
  };

  const safeText = (value) => (value || "").toString().trim();

  const ensureSession = () => {
    let sessionId = localStorage.getItem(STORAGE_KEY);
    if (!sessionId) {
      sessionId = (crypto && crypto.randomUUID)
        ? crypto.randomUUID()
        : `sess_${Date.now()}_${Math.random().toString(16).slice(2)}`;
      localStorage.setItem(STORAGE_KEY, sessionId);
    }
    state.sessionId = sessionId;
    const urlLabel = new URLSearchParams(window.location.search).get("telemetry_label");
    if (urlLabel && urlLabel.trim()) {
      localStorage.setItem(LABEL_KEY, urlLabel.trim());
    }
    let label = localStorage.getItem(LABEL_KEY) || "";
    if (!label && !sessionStorage.getItem(LABEL_PROMPT_KEY)) {
      sessionStorage.setItem(LABEL_PROMPT_KEY, "true");
      const input = window.prompt(
        "Telemetry session label (e.g., Admin-01, Doctor-02). Leave blank to skip:"
      );
      if (input && input.trim()) {
        label = input.trim();
        localStorage.setItem(LABEL_KEY, label);
      }
    }
    state.sessionLabel = label || "unlabeled";
  };

  const shouldRedact = (target) => {
    if (!target) return true;
    const name = safeText(target.name).toLowerCase();
    const id = safeText(target.id).toLowerCase();
    const type = safeText(target.type).toLowerCase();
    const sensitive = ["password", "passcode", "token", "totp", "otp", "secret"];
    return sensitive.some((key) => name.includes(key) || id.includes(key) || type.includes(key));
  };

  const elementMeta = (el) => {
    if (!el) return {};
    return {
      element_tag: el.tagName ? el.tagName.toLowerCase() : "",
      element_id: safeText(el.id),
      element_name: safeText(el.name),
      element_classes: el.className ? el.className.toString() : "",
    };
  };

  const enqueue = (event) => {
    state.queue.push(event);
    if (state.queue.length >= MAX_QUEUE) {
      flush();
    }
  };

  const buildBase = () => ({
    timestamp: new Date().toISOString(),
    session_id: state.sessionId,
    session_label: state.sessionLabel,
    page: window.location.pathname,
    title: document.title,
    referrer: document.referrer || "",
    viewport_w: window.innerWidth,
    viewport_h: window.innerHeight,
    screen_w: window.screen.width,
    screen_h: window.screen.height,
    timezone_offset: new Date().getTimezoneOffset(),
    language: navigator.language || "",
    online: navigator.onLine ? 1 : 0,
    connection_type: navigator.connection ? navigator.connection.effectiveType || "" : "",
  });

  const sendPayload = (payload) => {
    const body = JSON.stringify(payload);
    if (navigator.sendBeacon) {
      const blob = new Blob([body], { type: "application/json" });
      navigator.sendBeacon(ENDPOINT, blob);
      return;
    }
    fetch(ENDPOINT, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body,
      keepalive: true,
      credentials: "same-origin",
    }).catch(() => {});
  };

  const flush = () => {
    if (!state.queue.length) {
      return;
    }
    const batch = state.queue.splice(0, state.queue.length);
    sendPayload({ batch });
    state.lastFlush = Date.now();
  };

  const trackPageView = () => {
    let loadMs = 0;
    try {
      const timing = performance.timing;
      loadMs = timing.loadEventEnd - timing.navigationStart;
      if (loadMs < 0) {
        loadMs = 0;
      }
    } catch (_) {
      loadMs = 0;
    }
    enqueue({
      ...buildBase(),
      event_type: "page_view",
      duration_ms: 0,
      load_ms: loadMs,
    });
  };

  const trackClick = (event) => {
    state.clickCount += 1;
    const target = event.target;
    enqueue({
      ...buildBase(),
      event_type: "click",
      ...elementMeta(target),
      x: event.clientX,
      y: event.clientY,
    });
  };

  const trackSubmit = (event) => {
    enqueue({
      ...buildBase(),
      event_type: "form_submit",
      ...elementMeta(event.target),
    });
  };

  const trackInput = (event) => {
    const target = event.target;
    const value = shouldRedact(target)
      ? ""
      : safeText(target.value || target.textContent);
    const key = `${target?.tagName || "input"}:${safeText(target?.id)}:${safeText(target?.name)}`;
    const lastValue = state.inputCache.get(key);
    if (lastValue === value) {
      return;
    }
    state.inputCache.set(key, value);
    state.inputCount += 1;
    enqueue({
      ...buildBase(),
      event_type: "input_change",
      ...elementMeta(target),
      value,
    });
  };

  const trackError = (message, source) => {
    enqueue({
      ...buildBase(),
      event_type: "error",
      value: `${message || "unknown"} ${source || ""}`.trim(),
    });
  };

  const trackVisibility = () => {
    enqueue({
      ...buildBase(),
      event_type: document.hidden ? "tab_hidden" : "tab_visible",
    });
  };

  const trackExit = () => {
    const duration = Date.now() - state.pageStart;
    sendPayload({
      batch: [
        {
          ...buildBase(),
          event_type: "page_exit",
          duration_ms: duration,
          scroll_depth: Math.round(state.maxScrollPct),
          click_count: state.clickCount,
          input_count: state.inputCount,
          key_count: state.keyCount,
          idle_ms: state.idleMs,
        },
      ],
    });
  };

  const trackScroll = () => {
    const now = Date.now();
    if (now - state.lastScrollEmit < SCROLL_THROTTLE_MS) {
      return;
    }
    state.lastScrollEmit = now;
    const scrollTop = window.scrollY || document.documentElement.scrollTop || 0;
    const docHeight = document.documentElement.scrollHeight - window.innerHeight;
    if (docHeight <= 0) {
      return;
    }
    const pct = Math.min(100, Math.max(0, (scrollTop / docHeight) * 100));
    if (pct > state.maxScrollPct) {
      state.maxScrollPct = pct;
    }
    enqueue({
      ...buildBase(),
      event_type: "scroll",
      scroll_depth: Math.round(pct),
    });
  };

  const trackKey = () => {
    state.keyCount += 1;
  };

  const trackIdle = () => {
    const now = Date.now();
    const delta = now - state.lastIdleCheck;
    state.lastIdleCheck = now;
    if (now - state.lastActivity > 15000) {
      state.idleMs += delta;
    }
  };

  const trackActivity = () => {
    state.lastActivity = Date.now();
  };

  ensureSession();
  trackPageView();

  document.addEventListener("click", trackClick, { passive: true });
  document.addEventListener("submit", trackSubmit, { passive: true });
  document.addEventListener("change", trackInput, { passive: true });
  document.addEventListener("input", trackInput, { passive: true });
  document.addEventListener("visibilitychange", trackVisibility);
  document.addEventListener("keydown", trackKey, { passive: true });
  document.addEventListener("mousemove", trackActivity, { passive: true });
  document.addEventListener("scroll", trackScroll, { passive: true });
  window.addEventListener("beforeunload", trackExit);

  window.addEventListener("error", (event) => {
    trackError(event.message, event.filename);
  });
  window.addEventListener("unhandledrejection", (event) => {
    trackError(event.reason && event.reason.message, "unhandledrejection");
  });

  setInterval(flush, FLUSH_INTERVAL_MS);
  setInterval(trackIdle, 5000);
})();
