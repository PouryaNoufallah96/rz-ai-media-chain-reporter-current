import http from 'http';
import fs from 'fs';
import path from 'path';
import zlib from 'zlib';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const PORT = 3000;
const DIST = path.join(__dirname, 'frontend', 'dist');

const MIME = {
  '.html': 'text/html',
  '.css': 'text/css',
  '.js': 'application/javascript',
  '.mjs': 'application/javascript',
  '.json': 'application/json',
  '.png': 'image/png',
  '.jpg': 'image/jpeg',
  '.jpeg': 'image/jpeg',
  '.gif': 'image/gif',
  '.svg': 'image/svg+xml',
  '.webp': 'image/webp',
  '.ico': 'image/x-icon',
  '.woff': 'font/woff',
  '.woff2': 'font/woff2',
};

const FALLBACK = path.join(DIST, 'index.html');

// Text-ish assets compress 70-85% with gzip — sending them pre-compressed
// (mirrors the gzip already applied to backend API responses) avoids the
// truncated-transfer / blank-page issue large uncompressed bundles hit over
// flaky connections. Cache the gzip'd buffer per file since dist/ is static.
const COMPRESSIBLE = new Set(['.html', '.css', '.js', '.mjs', '.json', '.svg']);
const gzipCache = new Map();

function send(req, res, filePath, contentType) {
  fs.readFile(filePath, (err, data) => {
    if (err) return sendFallback(res);

    const ext = path.extname(filePath).toLowerCase();
    const acceptsGzip = (req.headers['accept-encoding'] || '').includes('gzip');
    const cacheControl = ext === '.html'
      ? 'no-store'
      : 'public, max-age=31536000, immutable';

    if (acceptsGzip && COMPRESSIBLE.has(ext)) {
      let gz = gzipCache.get(filePath);
      if (!gz) { gz = zlib.gzipSync(data); gzipCache.set(filePath, gz); }
      res.writeHead(200, {
        'Content-Type': contentType,
        'Content-Encoding': 'gzip',
        'Content-Length': gz.length,
        'Cache-Control': cacheControl,
      });
      return res.end(gz);
    }

    res.writeHead(200, { 'Content-Type': contentType, 'Content-Length': data.length, 'Cache-Control': cacheControl });
    res.end(data);
  });
}

function sendFallback(res) {
  // SPA fallback: unknown paths → index.html (React Router handles routing)
  fs.readFile(FALLBACK, (err2, html) => {
    if (err2) { res.writeHead(404); res.end('Not found'); return; }
  res.writeHead(200, { 'Content-Type': 'text/html', 'Content-Length': html.length, 'Cache-Control': 'no-store' });
    res.end(html);
  });
}

function proxyApi(req, res) {
  const upstream = http.request({
    hostname: '127.0.0.1',
    port: 3001,
    path: req.url,
    method: req.method,
    headers: { ...req.headers, host: '127.0.0.1:3001' },
  }, (upstreamRes) => {
    res.writeHead(upstreamRes.statusCode || 502, upstreamRes.headers);
    upstreamRes.pipe(res);
  });

  upstream.on('error', () => {
    if (!res.headersSent) {
      res.writeHead(502, { 'Content-Type': 'application/json' });
    }
    res.end(JSON.stringify({ error: 'Backend service is unavailable' }));
  });

  req.pipe(upstream);
}

const server = http.createServer((req, res) => {
  let urlPath = req.url.split('?')[0];
  if (urlPath.startsWith('/api/')) return proxyApi(req, res);
  if (urlPath === '/') urlPath = '/index.html';

  const filePath = path.join(DIST, urlPath);
  const ext = path.extname(filePath).toLowerCase();
  const contentType = MIME[ext] || 'application/octet-stream';

  send(req, res, filePath, contentType);
});

server.listen(PORT, () => {
  console.log(`ChainReporter frontend → http://localhost:${PORT}`);
});
