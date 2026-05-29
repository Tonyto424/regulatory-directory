#!/usr/bin/env node
/**
 * 每日爬虫：从官方源头抓取最新法规和案例，增量更新 index.html
 * 用法: node scripts/crawl_and_update.js
 * 自动: 每天早8点 cron 触发
 */

const fs = require('fs');
const path = require('path');
const http = require('http');
const https = require('https');

const META_FILE = path.join(__dirname, '..', '_metadata.json');
const HTML_FILE = path.join(__dirname, '..', 'index.html');

// ---------- helpers ----------
function fetch(url) {
  return new Promise((resolve, reject) => {
    const mod = url.startsWith('https') ? https : http;
    mod.get(url, { timeout: 15000 }, (res) => {
      let data = '';
      res.on('data', (chunk) => data += chunk);
      res.on('end', () => {
        if (res.statusCode >= 200 && res.statusCode < 400) resolve(data);
        else reject(new Error(`HTTP ${res.statusCode} for ${url}`));
      });
    }).on('error', reject).on('timeout', function() { this.destroy(); reject(new Error('timeout')); });
  });
}

function extractListings(html, baseUrl) {
  // Extract list items from CAC-style pages: <li>...<a href="...">Title</a>...</li>
  const results = [];
  const liRegex = /<li[^>]*>[\s\S]*?<\/li>/gi;
  let m;
  while ((m = liRegex.exec(html)) !== null) {
    const li = m[0];
    const aMatch = li.match(/<a[^>]+href="([^"]+)"[^>]*>([\s\S]*?)<\/a>/i);
    if (aMatch) {
      let href = aMatch[1].trim();
      let title = aMatch[2].replace(/<[^>]+>/g, '').trim();
      if (href.startsWith('//')) href = 'https:' + href;
      else if (href.startsWith('/')) href = new URL(href, baseUrl).href;
      // Extract date
      const dateMatch = li.match(/(\d{4}-\d{2}-\d{2})/);
      const date = dateMatch ? dateMatch[1] : '';
      // Skip non-law entries (commentary, photos, etc)
      const skipWords = ['专家解读', '一图读懂', '新闻', '公告', '通知'];
      if (!skipWords.some(w => title.includes(w))) {
        results.push({ title: title.trim(), url: href, date: date });
      }
    }
  }
  return results;
}

// ---------- main ----------
async function main() {
  console.log('[crawl] Starting daily crawl...');
  
  // Load metadata
  let meta;
  try {
    meta = JSON.parse(fs.readFileSync(META_FILE, 'utf8'));
  } catch(e) {
    meta = { knownLaws: [], knownCases: [], lastCrawl: '' };
  }
  const knownLaws = new Set(meta.knownLaws);
  const knownCases = new Set(meta.knownCases);
  
  // ------ CRAWL SOURCES ------
  console.log('[crawl] Fetching CAC sources...');
  
  const sources = [
    { url: 'https://www.cac.gov.cn/wxzw/zcfg/fl/A09370301index_1.htm', type: 'law' },
    { url: 'https://www.cac.gov.cn/wxzw/zcfg/xzfg/A09370302index_1.htm', type: 'regulation' },
    { url: 'https://www.cac.gov.cn/wxzw/zcfg/bmgz/A09370303index_1.htm', type: 'rule' },
    { url: 'https://www.cac.gov.cn/wxzw/zcfg/gfxwj/A09370305index_1.htm', type: 'rule' },
    { url: 'https://www.cac.gov.cn/wxzw/zcfg/zcwj/A09370306index_1.htm', type: 'policy' },
  ];
  
  const allListings = [];
  for (const src of sources) {
    try {
      const html = await fetch(src.url);
      const listings = extractListings(html, src.url);
      console.log(`  ${src.url.slice(0,60)}... -> ${listings.length} items`);
      allListings.push(...listings);
    } catch(e) {
      console.log(`  ${src.url.slice(0,60)}... FAILED: ${e.message}`);
    }
  }
  
  // ------ DETECT NEW LAWS ------
  const newLaws = [];
  for (const item of allListings) {
    // Normalize: remove "关于印发《" and "》的通知" etc
    let title = item.title;
    title = title.replace(/关于印发《/, '').replace(/》的通知/, '').replace(/^《/, '').replace(/》$/, '');
    // Check if any known law is a substring
    let found = false;
    for (const known of knownLaws) {
      if (title.includes(known) || known.includes(title)) {
        found = true;
        break;
      }
    }
    if (!found) {
      newLaws.push(item);
    }
  }
  
  console.log(`\n[crawl] New laws found: ${newLaws.length}`);
  for (const nl of newLaws.slice(0,5)) {
    console.log(`  NEW: ${nl.title} (${nl.date})`);
  }
  if (newLaws.length > 5) console.log(`  ... and ${newLaws.length-5} more`);
  
  // ------ UPDATE METADATA ------
  const now = new Date().toISOString().slice(0, 10) + ' ' + new Date().toTimeString().slice(0, 8);
  meta.lastCrawl = now;
  
  if (newLaws.length > 0) {
    // Add new law names to known set (simplified)
    for (const nl of newLaws) {
      knownLaws.add(nl.title);
    }
    meta.knownLaws = Array.from(knownLaws);
  }
  
  fs.writeFileSync(META_FILE, JSON.stringify(meta, null, 2), 'utf8');
  console.log(`\n[crawl] Metadata saved. Last crawl: ${now}`);
  console.log(`[crawl] Total known laws: ${meta.knownLaws.length}`);
  
  // ------ UPDATE HTML (mark new items) ------
  if (newLaws.length > 0) {
    console.log(`[crawl] ${newLaws.length} new items detected - would update HTML (manual integration pending)`);
    // For now, just write the new items to a report file
    const report = `# 新增法规/案例报告\n\n爬取时间: ${now}\n\n## 新增法规\n` +
      newLaws.map(l => `- ${l.title} (${l.date}) ${l.url}`).join('\n') +
      `\n\n## 新增案例\n(待手动整理)\n`;
    fs.writeFileSync(path.join(__dirname, '..', '_new_items.md'), report, 'utf8');
    console.log('[crawl] Report written to _new_items.md');
  }
  
  console.log('[crawl] Done!');
}

main().catch(e => {
  console.error('[crawl] Fatal:', e.message);
  process.exit(1);
});
