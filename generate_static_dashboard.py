#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
生成自包含的静态舆情看板 HTML
- 读取 SQLite 数据库
- 将数据内嵌到 dashboard/templates/index.html 中
- 覆盖 fetch API，使静态文件无需后端即可展示全部数据并支持时间筛选
- 改动（v3）:
  1. 月度总结用 published_at 切月（保留 2020-至今 全部月份）
  2. 月度 chips 显示 2026 年 1-12 月（含当月及历史），没数据占位 0
  3. 月度 chips 按月切换 + "全部" 选项（默认显示 2026 年全部月份）
  4. 每日页改为"当日 / 日期范围" 两套独立控件
  5. 每日页移除银行筛选
  6. 月度/每日 时间筛选独立
"""
import json
import os
import sqlite3
import re
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "data", "opinion.db")
TEMPLATE_PATH = os.path.join(BASE_DIR, "dashboard", "templates", "index.html")
OUTPUT_PATH = os.path.join(BASE_DIR, "static_dashboard.html")


def _ym_of(s):
    """从 published_at 里抽出 YYYY-MM；不是标准日期格式就 None"""
    if not s:
        return None
    s = str(s).strip()
    m = re.match(r"^(\d{4})-(\d{2})", s)
    if m:
        return f"{m.group(1)}-{m.group(2)}"
    return None


def _year_of(s):
    m = _ym_of(s)
    return int(m[:4]) if m else None


def export_data():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    cur.execute("SELECT * FROM articles ORDER BY crawled_at DESC")
    articles = [dict(r) for r in cur.fetchall()]

    # 用 published_at 给每条记录补一个 ym 字段（前端筛选/切月用）
    for a in articles:
        a["_ym"] = _ym_of(a.get("published_at") or a.get("crawled_at"))

    # 按银行
    cur.execute("""
        SELECT bank, COUNT(*) as count,
               SUM(CASE WHEN sentiment='正面' THEN 1 ELSE 0 END) as positive,
               SUM(CASE WHEN sentiment='负面' THEN 1 ELSE 0 END) as negative
        FROM articles GROUP BY bank ORDER BY count DESC
    """)
    by_bank = [dict(r) for r in cur.fetchall()]

    # 全局统计
    cur.execute("""
        SELECT COUNT(*) as total,
               SUM(CASE WHEN sentiment='正面' THEN 1 ELSE 0 END) as positive,
               SUM(CASE WHEN sentiment='负面' THEN 1 ELSE 0 END) as negative
        FROM articles
    """)
    stats = dict(cur.fetchone())

    # ====== 月度总结：用 published_at 切月 ======
    cur.execute("""
        SELECT substr(published_at, 1, 7) as month,
               bank,
               COUNT(*) as count,
               SUM(CASE WHEN sentiment='正面' THEN 1 ELSE 0 END) as positive,
               SUM(CASE WHEN sentiment='负面' THEN 1 ELSE 0 END) as negative
        FROM articles
        WHERE published_at IS NOT NULL AND published_at != ''
          AND length(published_at) >= 10 AND substr(published_at, 5, 1) = '-'
        GROUP BY substr(published_at, 1, 7), bank
        ORDER BY month DESC
    """)
    monthly_rows = cur.fetchall()
    months = {}
    for r in monthly_rows:
        m = r["month"]
        if m not in months:
            months[m] = {
                "month": m,
                "total": 0, "positive": 0, "negative": 0,
                "by_bank": [], "top_keywords": [],
                "top_keywords_by_bank": {},
            }
        entry = months[m]
        entry["total"] += r["count"]
        entry["positive"] += r["positive"] or 0
        entry["negative"] += r["negative"] or 0
        entry["by_bank"].append({
            "bank": r["bank"],
            "count": r["count"],
            "positive": r["positive"] or 0,
            "negative": r["negative"] or 0,
        })

    # 当年 1-12 月占位（即使没数据也展示）
    current_year = datetime.now().year
    for mm in range(1, 13):
        m = f"{current_year}-{mm:02d}"
        if m not in months:
            months[m] = {
                "month": m, "total": 0, "positive": 0, "negative": 0,
                "by_bank": [], "top_keywords": [],
                "top_keywords_by_bank": {},
            }

    for m in months:
        # 当月全银行热门词条
        kw_rows = cur.execute("""
            SELECT keyword, COUNT(*) as count,
                   SUM(CASE WHEN sentiment='正面' THEN 1 ELSE 0 END) as positive,
                   SUM(CASE WHEN sentiment='负面' THEN 1 ELSE 0 END) as negative
            FROM articles
            WHERE substr(published_at, 1, 7) = ?
              AND length(published_at) >= 10
            GROUP BY keyword ORDER BY count DESC LIMIT 5
        """, (m,)).fetchall()
        months[m]["top_keywords"] = [dict(r) for r in kw_rows]

        # 当月每家银行的热门词条
        for bank_entry in months[m]["by_bank"]:
            bank = bank_entry["bank"]
            bank_kw_rows = cur.execute("""
                SELECT keyword, COUNT(*) as count,
                       SUM(CASE WHEN sentiment='正面' THEN 1 ELSE 0 END) as positive,
                       SUM(CASE WHEN sentiment='负面' THEN 1 ELSE 0 END) as negative
                FROM articles
                WHERE substr(published_at, 1, 7) = ? AND bank = ?
                  AND length(published_at) >= 10
                GROUP BY keyword ORDER BY count DESC LIMIT 5
            """, (m, bank)).fetchall()
            months[m]["top_keywords_by_bank"][bank] = [dict(r) for r in bank_kw_rows]

    for entry in months.values():
        entry["by_bank"].sort(key=lambda x: (x["bank"] != "工商银行", -x["count"]))

    # 只显示 2026 年 1月~当前月；之前的归入 "history" 里
    now_month = datetime.now().strftime("%Y-%m")
    monthly = []
    for m, entry in months.items():
        if m.startswith(f"{current_year}-") and m <= now_month:
            monthly.append(entry)
    # 之前的（2025 及更早）按月单独存，并入 monthly 一并展示
    history = [v for k, v in months.items() if not k.startswith(f"{current_year}-")]
    history.sort(key=lambda x: x["month"], reverse=True)
    monthly.extend(history)
    monthly.sort(key=lambda x: x["month"], reverse=True)

    conn.close()
    return {
        "stats": stats,
        "by_bank": by_bank,
        "articles": articles,
        "monthly": monthly,
    }


def build_embed_script(data: dict) -> str:
    data_json = json.dumps(data, ensure_ascii=False, indent=2)
    return f"""
<script>
// Embedded data - no server needed
const EMBEDDED_DATA = {data_json};
window.EMBEDDED_DATA = EMBEDDED_DATA;

function parseEmbeddedDate(s) {{
  if (!s) return null;
  const d = new Date(String(s).replace(/-/g, '/'));
  return isNaN(d.getTime()) ? null : d;
}}

function getArticleMonth(a) {{
  // 优先 published_at（YYYY-MM-DD），其次 crawled_at，最后用 _ym
  if (a._ym) return a._ym;
  const p = a.published_at || '';
  const m = String(p).match(/^(\\d{{4}})-(\\d{{2}})/);
  if (m) return m[1] + '-' + m[2];
  const c = a.crawled_at || '';
  const m2 = String(c).match(/^(\\d{{4}})-(\\d{{2}})/);
  if (m2) return m2[1] + '-' + m2[2];
  return null;
}}

function filterEmbeddedArticles(articles, bank, source, dateFrom, dateTo) {{
  if (!articles) return [];
  let list = articles.slice();
  if (bank) {{
    list = list.filter(a => a.bank === bank);
  }}
  if (source) {{
    list = list.filter(a => a.source === source);
  }}
  if (dateFrom || dateTo) {{
    const from = dateFrom ? new Date(dateFrom + 'T00:00:00') : null;
    const to = dateTo ? new Date(dateTo + 'T23:59:59') : null;
    list = list.filter(a => {{
      const d = parseEmbeddedDate(a.published_at || a.crawled_at);
      if (!d) return false;
      if (from && d < from) return false;
      if (to && d > to) return false;
      return true;
    }});
  }}
  return list;
}}

function computeStats(articles) {{
  const total = articles.length;
  const positive = articles.filter(a => a.sentiment === '正面').length;
  const negative = articles.filter(a => a.sentiment === '负面').length;
  const bankMap = {{}};
  for (const a of articles) {{
    if (!bankMap[a.bank]) bankMap[a.bank] = {{ bank: a.bank, count: 0, positive: 0, negative: 0 }};
    bankMap[a.bank].count++;
    if (a.sentiment === '正面') bankMap[a.bank].positive++;
    if (a.sentiment === '负面') bankMap[a.bank].negative++;
  }}
  return {{ total, positive, negative, by_bank: Object.values(bankMap).sort((a,b) => b.count - a.count) }};
}}

function computeMonthly(articles) {{
  // 用 _ym / published_at / crawled_at 抽 YYYY-MM
  const months = {{}};
  for (const a of articles) {{
    const m = getArticleMonth(a);
    if (!m) continue;
    if (!months[m]) months[m] = {{
      month: m, total: 0, positive: 0, negative: 0,
      by_bank: [], top_keywords: [], top_keywords_by_bank: {{}}
    }};
    const entry = months[m];
    entry.total++;
    if (a.sentiment === '正面') entry.positive++;
    if (a.sentiment === '负面') entry.negative++;
    let b = entry.by_bank.find(x => x.bank === a.bank);
    if (b) {{ b.count++; if (a.sentiment === '正面') b.positive++; if (a.sentiment === '负面') b.negative++; }}
    else entry.by_bank.push({{ bank: a.bank, count: 1, positive: a.sentiment === '正面' ? 1 : 0, negative: a.sentiment === '负面' ? 1 : 0 }});
  }}
  // 每家银行各自的热门词条
  for (const m in months) {{
    const entry = months[m];
    entry.by_bank.sort((a,b) => (a.bank !== '工商银行') - (b.bank !== '工商银行') || b.count - a.count);
    for (const b of entry.by_bank) {{
      const kwMap = {{}};
      for (const a of articles) {{
        if (getArticleMonth(a) !== m) continue;
        if (a.bank !== b.bank) continue;
        if (!kwMap[a.keyword]) kwMap[a.keyword] = {{ keyword: a.keyword, count: 0, positive: 0, negative: 0 }};
        kwMap[a.keyword].count++;
        if (a.sentiment === '正面') kwMap[a.keyword].positive++;
        if (a.sentiment === '负面') kwMap[a.keyword].negative++;
      }}
      entry.top_keywords_by_bank[b.bank] = Object.values(kwMap).sort((a,b) => b.count - a.count).slice(0, 5);
    }}
    // 全银行热门词条
    const kwMap = {{}};
    for (const a of articles) {{
      if (getArticleMonth(a) !== m) continue;
      if (!kwMap[a.keyword]) kwMap[a.keyword] = {{ keyword: a.keyword, count: 0, positive: 0, negative: 0 }};
      kwMap[a.keyword].count++;
      if (a.sentiment === '正面') kwMap[a.keyword].positive++;
      if (a.sentiment === '负面') kwMap[a.keyword].negative++;
    }}
    entry.top_keywords = Object.values(kwMap).sort((a,b) => b.count - a.count).slice(0, 5);
  }}
  // 补齐当年 1月~当前月空数据（占位）
  const now = new Date();
  const year = now.getFullYear();
  const ymNow = year + '-' + String(now.getMonth() + 1).padStart(2, '0');
  for (let mm = 1; mm <= now.getMonth() + 1; mm++) {{
    const m = year + '-' + String(mm).padStart(2, '0');
    if (!months[m]) months[m] = {{
      month: m, total: 0, positive: 0, negative: 0,
      by_bank: [], top_keywords: [], top_keywords_by_bank: {{}}
    }};
  }}
  return Object.values(months)
    .filter(x => x.month <= ymNow)
    .sort((a,b) => b.month.localeCompare(a.month));
}}

// Override fetch to use embedded data
const originalFetch = window.fetch;
window.fetch = function(url) {{
  return new Promise((resolve) => {{
    const urlStr = String(url);
    const searchParams = new URLSearchParams(urlStr.split('?')[1] || '');
    const bank = searchParams.get('bank') || '';
    const source = searchParams.get('source') || '';
    const dateFrom = searchParams.get('date_from') || '';
    const dateTo = searchParams.get('date_to') || '';
    let data = null;

    if (urlStr.includes('/api/stats')) {{
      const filtered = filterEmbeddedArticles(EMBEDDED_DATA.articles, bank, source, dateFrom, dateTo);
      data = computeStats(filtered);
    }}
    else if (urlStr.includes('/api/monthly')) {{
      const filtered = filterEmbeddedArticles(EMBEDDED_DATA.articles, bank, source, dateFrom, dateTo);
      data = computeMonthly(filtered);
    }}
    else if (urlStr.match(/\\/api\\/month\\/([^?]+)/)) {{
      const month = urlStr.match(/\\/api\\/month\\/([^?]+)/)[1];
      const filtered = filterEmbeddedArticles(EMBEDDED_DATA.articles, bank, source, dateFrom, dateTo)
        .filter(a => getArticleMonth(a) === month);
      data = filtered;
    }}
    else if (urlStr.includes('/api/articles')) {{
      const keyword = searchParams.get('keyword') || '';
      const srcFilter = searchParams.get('source') || '';
      const sentiment = searchParams.get('sentiment') || '';
      const limit = parseInt(searchParams.get('limit') || '500');
      let filtered = filterEmbeddedArticles(EMBEDDED_DATA.articles, bank, source, dateFrom, dateTo);
      if (keyword) filtered = filtered.filter(a => a.keyword === keyword);
      if (srcFilter) filtered = filtered.filter(a => a.source === srcFilter);
      if (sentiment) filtered = filtered.filter(a => a.sentiment === sentiment);
      data = filtered.slice(0, limit);
    }}
    else {{
      data = {{}};
    }}

    resolve({{
      json: () => Promise.resolve(data)
    }});
  }});
}};
</script>
"""


def generate():
    data = export_data()
    with open(TEMPLATE_PATH, "r", encoding="utf-8") as f:
        html = f.read()

    embed_script = build_embed_script(data)
    # Insert right before the first <script> tag
    html = html.replace("<script>", embed_script + "\n<script>", 1)

    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"Static dashboard generated: {OUTPUT_PATH}")
    print(f"File size: {len(html) / 1024:.1f} KB")
    print(f"Articles embedded: {len(data['articles'])}")
    print(f"Months in monthly summary: {len(data['monthly'])}")


if __name__ == "__main__":
    generate()
