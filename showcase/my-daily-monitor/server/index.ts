/**
 * Production server for Agents Monitor.
 * Serves the built single-page app and exposes the same API routes used in development.
 *
 * Usage: node server-dist/server/index.js
 */

import http from 'node:http';
import { createReadStream, existsSync } from 'node:fs';
import { stat } from 'node:fs/promises';
import { extname, join, normalize } from 'node:path';
import { parse as parseUrl } from 'node:url';
import { routeHandlers } from './routes';

const PORT = Number(
  process.env.PORT ||
  process.env.API_PORT ||
  (process.env.NODE_ENV === 'production' ? 5173 : 3001)
);
const DIST_DIR = join(process.cwd(), 'dist');
const INDEX_FILE = join(DIST_DIR, 'index.html');

const CONTENT_TYPES: Record<string, string> = {
  '.css': 'text/css; charset=utf-8',
  '.gif': 'image/gif',
  '.html': 'text/html; charset=utf-8',
  '.ico': 'image/x-icon',
  '.jpeg': 'image/jpeg',
  '.jpg': 'image/jpeg',
  '.js': 'text/javascript; charset=utf-8',
  '.json': 'application/json; charset=utf-8',
  '.map': 'application/json; charset=utf-8',
  '.png': 'image/png',
  '.svg': 'image/svg+xml',
  '.txt': 'text/plain; charset=utf-8',
  '.webp': 'image/webp',
  '.woff': 'font/woff',
  '.woff2': 'font/woff2',
};

function setCorsHeaders(res: http.ServerResponse): void {
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type, X-API-Key, X-Finnhub-Key, X-Github-Token, X-Feishu-App-Id, X-Feishu-App-Secret, X-Twitter-Token, X-Gmail-Token, X-OpenRouter-Key, X-MS-Client-Id, X-MS-Client-Secret, X-MS-Tenant-Id');
  res.setHeader('Access-Control-Allow-Methods', 'GET, POST, OPTIONS');
}

async function readBody(req: http.IncomingMessage): Promise<string> {
  let body = '';
  if (req.method === 'POST') {
    for await (const chunk of req) body += chunk;
  }
  return body;
}

function sendJson(res: http.ServerResponse, statusCode: number, payload: unknown): void {
  res.writeHead(statusCode, { 'Content-Type': 'application/json; charset=utf-8' });
  res.end(JSON.stringify(payload));
}

function safeAssetPath(pathname: string): string | null {
  const decodedPath = decodeURIComponent(pathname);
  const stripped = decodedPath.replace(/^\/+/, '');
  const normalized = normalize(stripped);
  if (!normalized || normalized.startsWith('..') || normalized.includes('..\\') || normalized.includes('../')) {
    return null;
  }
  return join(DIST_DIR, normalized);
}

async function tryServeAsset(pathname: string, res: http.ServerResponse): Promise<boolean> {
  const assetPath = safeAssetPath(pathname);
  if (!assetPath) {
    sendJson(res, 400, { error: 'Invalid path' });
    return true;
  }

  try {
    const assetStat = await stat(assetPath);
    if (!assetStat.isFile()) {
      return false;
    }
  } catch {
    return false;
  }

  const extension = extname(assetPath).toLowerCase();
  res.writeHead(200, {
    'Content-Type': CONTENT_TYPES[extension] || 'application/octet-stream',
    'Cache-Control': extension === '.html' ? 'no-cache' : 'public, max-age=31536000, immutable',
  });
  createReadStream(assetPath).pipe(res);
  return true;
}

const server = http.createServer(async (req, res) => {
  setCorsHeaders(res);

  if (req.method === 'OPTIONS') { res.writeHead(204); res.end(); return; }

  const parsed = parseUrl(req.url || '/', true);
  const pathname = parsed.pathname || '/';
  const query: Record<string, string> = {};
  for (const [k, v] of Object.entries(parsed.query || {})) {
    query[k] = Array.isArray(v) ? v[0] || '' : v || '';
  }

  if (pathname === '/healthz') {
    sendJson(res, 200, {
      status: 'ok',
      distReady: existsSync(INDEX_FILE),
    });
    return;
  }

  const handler = routeHandlers[pathname];
  if (handler) {
    const body = await readBody(req);

    try {
      const result = await handler(query, body, req.headers);
      sendJson(res, 200, result);
    } catch (err: any) {
      console.error(`[API] ${pathname} error:`, err.message);
      sendJson(res, 500, { error: err.message || 'Internal error' });
    }
    return;
  }

  if (req.method !== 'GET' && req.method !== 'HEAD') {
    sendJson(res, 405, { error: 'Method not allowed' });
    return;
  }

  if (pathname !== '/' && await tryServeAsset(pathname, res)) {
    return;
  }

  if (!existsSync(INDEX_FILE)) {
    sendJson(res, 503, { error: 'Frontend build not found' });
    return;
  }

  res.writeHead(200, { 'Content-Type': 'text/html; charset=utf-8', 'Cache-Control': 'no-cache' });
  createReadStream(INDEX_FILE).pipe(res);
});

server.listen(PORT, () => {
  console.log(`[Agents Monitor] Production server running on http://localhost:${PORT}`);
});

