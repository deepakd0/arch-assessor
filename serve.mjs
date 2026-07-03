import http from "node:http";
import { readFile } from "node:fs/promises";
import { dirname, extname, join, normalize } from "node:path";
import { fileURLToPath } from "node:url";

const ROOT = dirname(fileURLToPath(import.meta.url));
const PORT = 4173;
const MIME = { ".html": "text/html", ".md": "text/plain; charset=utf-8", ".json": "application/json" };

http.createServer(async (req, res) => {
  try {
    let p = decodeURIComponent(new URL(req.url, "http://x").pathname);
    if (p.endsWith("/")) p += "GUIDE.html";
    const file = normalize(join(ROOT, p));
    if (!file.startsWith(ROOT)) { res.writeHead(403); res.end(); return; }
    const data = await readFile(file);
    res.writeHead(200, { "content-type": MIME[extname(file)] ?? "text/plain; charset=utf-8" });
    res.end(data);
  } catch {
    res.writeHead(404); res.end("not found");
  }
}).listen(PORT, () => console.log("serving " + ROOT + " on http://localhost:" + PORT));
