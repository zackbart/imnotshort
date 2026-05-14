import { join, resolve, normalize } from "node:path";

const PUBLIC = resolve(import.meta.dirname, "public");

const MIME = {
  ".html": "text/html; charset=utf-8",
  ".css":  "text/css; charset=utf-8",
  ".js":   "application/javascript; charset=utf-8",
  ".svg":  "image/svg+xml",
  ".png":  "image/png",
  ".jpg":  "image/jpeg",
  ".jpeg": "image/jpeg",
  ".ico":  "image/x-icon",
  ".usdz": "model/vnd.usdz+zip",
};

const headersFor = (path) => {
  const h = {};
  const ext = path.slice(path.lastIndexOf("."));
  if (MIME[ext]) h["Content-Type"] = MIME[ext];

  if (ext === ".usdz") {
    // Short cache so a pre-event fix actually reaches devices that already
    // visited the page. No Content-Disposition — AR Quick Look dispatch
    // is cleanest with just Content-Type set.
    h["Cache-Control"] = "public, max-age=300, must-revalidate";
  } else if (ext === ".html" || path === "/") {
    h["Cache-Control"] = "public, max-age=60, must-revalidate";
  } else {
    h["Cache-Control"] = "public, max-age=300";
  }
  h["X-Content-Type-Options"] = "nosniff";
  return h;
};

// ----- Slide-sync state (SSE) -----------------------------------------------
const state = { slide: 1 };
const TOTAL = 11;
const sseClients = new Set();
const encoder = new TextEncoder();

function broadcast(slide) {
  const payload = encoder.encode(`data: ${JSON.stringify({ slide })}\n\n`);
  for (const controller of sseClients) {
    try {
      controller.enqueue(payload);
    } catch {
      sseClients.delete(controller);
    }
  }
}

// Heartbeat survives `bun --hot` by stashing on globalThis so re-execution
// clears the old interval before spawning a new one.
if (globalThis.__ppniteHeartbeat) clearInterval(globalThis.__ppniteHeartbeat);
globalThis.__ppniteHeartbeat = setInterval(() => {
  const beat = encoder.encode(`: keepalive\n\n`);
  for (const controller of sseClients) {
    try {
      controller.enqueue(beat);
    } catch {
      sseClients.delete(controller);
    }
  }
}, 20_000);

const jsonResponse = (body, init = {}) =>
  new Response(JSON.stringify(body), {
    ...init,
    headers: {
      "Content-Type": "application/json; charset=utf-8",
      "Cache-Control": "no-store",
      "X-Content-Type-Options": "nosniff",
      ...(init.headers || {}),
    },
  });

const server = Bun.serve({
  port: Number(process.env.PORT) || 3000,
  hostname: "0.0.0.0",
  // SSE streams need a long idle timeout; heartbeats every 20s keep them warm.
  idleTimeout: 255,
  async fetch(req) {
    const url = new URL(req.url);

    // Railway terminates TLS at the edge and forwards the original scheme.
    // Force https so the browser never shows "Not Secure".
    if (req.headers.get("x-forwarded-proto") === "http") {
      return new Response(null, {
        status: 301,
        headers: { Location: `https://${url.host}${url.pathname}${url.search}` },
      });
    }

    let path;
    try {
      path = decodeURIComponent(url.pathname);
    } catch {
      return new Response("Bad Request", { status: 400 });
    }

    // ----- API & SSE routes -------------------------------------------------
    if (path === "/events" && req.method === "GET") {
      let thisController;
      const stream = new ReadableStream({
        start(controller) {
          thisController = controller;
          sseClients.add(controller);
          controller.enqueue(
            encoder.encode(`data: ${JSON.stringify({ slide: state.slide })}\n\n`),
          );
        },
        // The cancel() callback's argument is the cancellation reason, not the
        // controller — close over `thisController` so we delete the correct one.
        cancel() {
          sseClients.delete(thisController);
        },
      });
      return new Response(stream, {
        headers: {
          "Content-Type": "text/event-stream; charset=utf-8",
          "Cache-Control": "no-cache, no-transform",
          "X-Accel-Buffering": "no",
          Connection: "keep-alive",
        },
      });
    }

    if (path === "/api/state" && req.method === "GET") {
      return jsonResponse({ slide: state.slide });
    }

    if (path === "/api/slide" && req.method === "POST") {
      let body;
      try {
        body = await req.json();
      } catch {
        return jsonResponse({ error: "invalid_json" }, { status: 400 });
      }
      if (!body || typeof body !== "object") {
        return jsonResponse({ error: "invalid_body" }, { status: 400 });
      }
      let next;
      if ("slide" in body) {
        const n = body.slide;
        if (typeof n !== "number" || !Number.isInteger(n) || n < 1 || n > TOTAL) {
          return jsonResponse({ error: "invalid_slide" }, { status: 400 });
        }
        next = n;
      } else if ("delta" in body) {
        const d = body.delta;
        if (d !== 1 && d !== -1) {
          return jsonResponse({ error: "invalid_delta" }, { status: 400 });
        }
        next = Math.max(1, Math.min(TOTAL, state.slide + d));
      } else {
        return jsonResponse({ error: "missing_field" }, { status: 400 });
      }
      if (next !== state.slide) {
        state.slide = next;
        broadcast(state.slide);
      }
      return jsonResponse({ slide: state.slide });
    }

    // /demo bypasses the HTML page entirely so iOS opens its native AR
    // Quick Look preview straight from the USDZ. One less tap, no <a rel="ar">
    // dispatch fragility.
    if (path === "/demo" || path === "/demo/") {
      return new Response(null, {
        status: 302,
        headers: { Location: "/figure.usdz#allowsContentScaling=0" },
      });
    }

    // ----- Static files -----------------------------------------------------
    if (path === "/") path = "/index.html";
    else if (path === "/control" || path === "/control/") path = "/control.html";

    const filePath = normalize(join(PUBLIC, path));
    if (!filePath.startsWith(PUBLIC + "/") && filePath !== PUBLIC) {
      return new Response("Forbidden", { status: 403 });
    }

    const file = Bun.file(filePath);
    if (!(await file.exists())) {
      return new Response("Not Found", { status: 404 });
    }

    return new Response(file, { headers: headersFor(path) });
  },
});

console.log(`listening on http://${server.hostname}:${server.port}`);
