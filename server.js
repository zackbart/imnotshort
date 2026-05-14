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
    h["Cache-Control"] = "public, max-age=31536000, immutable";
    // AR Quick Look prefers being served as a single attachment.
    h["Content-Disposition"] = 'inline; filename="figure.usdz"';
  } else if (ext === ".html" || path === "/") {
    h["Cache-Control"] = "public, max-age=60, must-revalidate";
  } else {
    h["Cache-Control"] = "public, max-age=3600";
  }
  h["X-Content-Type-Options"] = "nosniff";
  return h;
};

const server = Bun.serve({
  port: Number(process.env.PORT) || 3000,
  hostname: "0.0.0.0",
  async fetch(req) {
    const url = new URL(req.url);
    let path = decodeURIComponent(url.pathname);
    if (path === "/") path = "/index.html";

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
