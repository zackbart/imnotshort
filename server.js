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

const server = Bun.serve({
  port: Number(process.env.PORT) || 3000,
  hostname: "0.0.0.0",
  async fetch(req) {
    const url = new URL(req.url);
    let path;
    try {
      path = decodeURIComponent(url.pathname);
    } catch {
      return new Response("Bad Request", { status: 400 });
    }
    if (path === "/") path = "/index.html";
    else if (path === "/demo" || path === "/demo/") path = "/demo/index.html";

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
