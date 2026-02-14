#!/usr/bin/env node
/**
 * 記事内の参考文献URLが存在・到達可能か検証する。
 * 使い方: node scripts/verify-reference-urls.mjs [path]
 *   path: 検証するディレクトリまたはファイル（省略時は articles/）
 * 終了コード: 0 = すべて成功, 1 = 1件以上失敗
 */

import { readFileSync, readdirSync, statSync } from "fs";
import { join, resolve } from "path";
import { fileURLToPath } from "url";

const __dirname = fileURLToPath(new URL(".", import.meta.url));
const repoRoot = resolve(__dirname, "..");
const defaultPath = join(repoRoot, "articles");

const TIMEOUT_MS = 12000;
const CONCURRENCY = 5;

// Markdown から URL を抽出（プレーンURL と [text](url) の両方）
const URL_REGEX =
  /https?:\/\/[^\s)\]`"<>]+|(?<=\]\()https?:\/\/[^)\s]+/g;

function* walkMd(dirOrFile) {
  const p = resolve(repoRoot, dirOrFile);
  const stat = statSync(p, { throwIfNoEntry: false });
  if (!stat) return;
  if (stat.isFile()) {
    if (p.endsWith(".md")) yield p;
    return;
  }
  if (stat.isDirectory()) {
    for (const name of readdirSync(p)) {
      const full = join(p, name);
      const s = statSync(full);
      if (s.isDirectory()) yield* walkMd(full);
      else if (name.endsWith(".md")) yield full;
    }
  }
}

function extractUrlsFromFile(filePath) {
  const text = readFileSync(filePath, "utf-8");
  const urls = [];
  let m;
  URL_REGEX.lastIndex = 0;
  while ((m = URL_REGEX.exec(text)) !== null) {
    let u = m[0];
    if (u.startsWith("](")) u = u.slice(2);
    u = u.replace(/[)\]`"<>]+$/, "").trim();
    if (u && !urls.includes(u)) urls.push(u);
  }
  return urls;
}

function collectUrlToFiles(dirOrFile) {
  const urlToFiles = new Map();
  for (const fp of walkMd(dirOrFile)) {
    const rel = fp.slice(repoRoot.length + 1);
    for (const url of extractUrlsFromFile(fp)) {
      if (!urlToFiles.has(url)) urlToFiles.set(url, []);
      urlToFiles.get(url).push(rel);
    }
  }
  return urlToFiles;
}

async function checkUrl(url) {
  const ac = new AbortController();
  const t = setTimeout(() => ac.abort(), TIMEOUT_MS);
  try {
    const res = await fetch(url, {
      method: "HEAD",
      redirect: "follow",
      signal: ac.signal,
      headers: { "User-Agent": "Zenn-Blog-Reference-Check/1.0" },
    });
    clearTimeout(t);
    return { status: res.status, ok: res.ok };
  } catch (e) {
    clearTimeout(t);
    if (e.name === "AbortError")
      return { status: 0, ok: false, error: "timeout" };
    try {
      const res = await fetch(url, {
        method: "GET",
        redirect: "follow",
        signal: AbortSignal.timeout(TIMEOUT_MS),
        headers: { "User-Agent": "Zenn-Blog-Reference-Check/1.0" },
      });
      return { status: res.status, ok: res.ok };
    } catch (e2) {
      return {
        status: 0,
        ok: false,
        error: e2.message || String(e2),
      };
    }
  }
}

async function runInBatches(items, batchSize, fn) {
  const results = [];
  for (let i = 0; i < items.length; i += batchSize) {
    const batch = items.slice(i, i + batchSize);
    results.push(...(await Promise.all(batch.map(fn))));
  }
  return results;
}

async function main() {
  const pathArg = process.argv[2] || defaultPath;
  const dirOrFile = pathArg.startsWith("/") ? pathArg : join(repoRoot, pathArg);

  console.log("Checking references under:", dirOrFile);
  const urlToFiles = collectUrlToFiles(dirOrFile);
  const urls = [...urlToFiles.keys()];
  if (urls.length === 0) {
    console.log("No URLs found.");
    process.exit(0);
  }

  console.log(`Found ${urls.length} unique URL(s). Checking...\n`);
  const results = await runInBatches(urls, CONCURRENCY, checkUrl);

  let ok = 0;
  let fail = 0;
  const failures = [];

  for (let i = 0; i < urls.length; i++) {
    const url = urls[i];
    const r = results[i];
    const files = urlToFiles.get(url);
    const fileList = files.length ? ` (${files.join(", ")})` : "";

    if (r.ok) {
      ok++;
      console.log(`OK  ${r.status}  ${url}`);
    } else {
      fail++;
      const err = r.error ? ` ${r.error}` : "";
      console.log(`FAIL  ${r.status || err}${fileList}`);
      console.log(url);
      failures.push({ url, status: r.status, error: r.error, files });
    }
  }

  console.log("\n---");
  console.log(`OK: ${ok}, FAIL: ${fail}`);

  if (fail > 0) {
    console.log("\nFailed URLs (click to open):");
    failures.forEach(({ url, status, error, files }) => {
      console.log(url);
      console.log(`  status: ${status || error}, in: ${files.join(", ")}`);
    });
  }

  process.exit(fail > 0 ? 1 : 0);
}

main().catch((e) => {
  console.error(e);
  process.exit(2);
});
