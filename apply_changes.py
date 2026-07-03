#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""一次性把模板改成：银行分词条 + 月份 chips + 每日时间独立。"""
import re

TEMPLATE = r'dashboard/templates/index.html'

with open(TEMPLATE, 'r', encoding='utf-8') as f:
    html = f.read()

# ========= 替换 1: renderMonthly 内部 bankRowsHtml 生成（每家银行带自己的词条） =========
old_bank = r'''    // Bank rows (ICBC first)
    let bankRowsHtml = '';
    for (const b of m.by_bank) {
      const isIcbc = b.bank === '工商银行';
      const total = b.count || 0;
      const pos = b.positive || 0;
      const neg = b.negative || 0;
      const posWidth = total > 0 ? (pos / total * 100) : 0;
      const negWidth = total > 0 ? (neg / total * 100) : 0;
      bankRowsHtml += `
        <div class="bank-row">
          <div class="bank-name ${isIcbc ? 'icbc' : ''}">
            <span class="dot"></span>${b.bank}
          </div>
          <div class="bar-container">
            <div class="bar-pos" style="width:${posWidth}%"></div>
            <div class="bar-neg" style="width:${negWidth}%"></div>
          </div>
          <div class="bank-counts">
            <span class="neg">${neg}负</span> / <span class="pos">${pos}正</span> / ${total}
          </div>
        </div>`;
    }'''

new_bank = r'''    // Bank rows (ICBC first) — 每家银行下面带各自热门词条
    let bankRowsHtml = '';
    for (const b of m.by_bank) {
      const isIcbc = b.bank === '工商银行';
      const total = b.count || 0;
      const pos = b.positive || 0;
      const neg = b.negative || 0;
      const posWidth = total > 0 ? (pos / total * 100) : 0;
      const negWidth = total > 0 ? (neg / total * 100) : 0;
      const bankKws = (m.top_keywords_by_bank && m.top_keywords_by_bank[b.bank]) || [];
      let bankKwHtml = '';
      if (bankKws.length > 0) {
        bankKwHtml = '<div class="bank-kw-block' + (isIcbc ? ' icbc' : '') + '">';
        bankKwHtml += '<div class="bank-kw-title">📌 ' + b.bank + ' 当月热门词条</div>';
        bankKwHtml += '<div class="keyword-tags">';
        for (const kw of bankKws) {
          const kn = kw.negative || 0;
          const kp = kw.positive || 0;
          bankKwHtml += '<span class="kw-tag"><span class="kw-count">' + kw.keyword + '</span><span class="kw-count">' + kw.count + '</span>';
          if (kn > 0) bankKwHtml += '<span class="kw-neg">' + kn + '负</span>';
          if (kp > 0) bankKwHtml += '<span class="kw-pos">' + kp + '正</span>';
          bankKwHtml += '</span>';
        }
        bankKwHtml += '</div></div>';
      }
      bankRowsHtml += `
        <div class="bank-row">
          <div class="bank-name ${isIcbc ? 'icbc' : ''}">
            <span class="dot"></span>${b.bank}
          </div>
          <div class="bar-container">
            <div class="bar-pos" style="width:${posWidth}%"></div>
            <div class="bar-neg" style="width:${negWidth}%"></div>
          </div>
          <div class="bank-counts">
            <span class="neg">${neg}负</span> / <span class="pos">${pos}正</span> / ${total}
          </div>
        </div>${bankKwHtml}`;
    }'''

if old_bank in html:
    html = html.replace(old_bank, new_bank, 1)
    print('Replaced 1: bank-row loop with per-bank keywords')
else:
    print('WARN: bank-row loop pattern not found')

# ========= 替换 2: renderMonthly 函数开头（加 chips + 过滤） =========
old_render = r'''function renderMonthly() {
  const container = document.getElementById('monthlyList');
  if (!monthlyData || monthlyData.length === 0) {
    container.innerHTML = '<div class="no-data">暂无数据</div>';
    return;
  }

  let html = '';'''

new_render = r'''function renderMonthly() {
  const container = document.getElementById('monthlyList');
  const chipsContainer = document.getElementById('monthlyChips');
  if (chipsContainer) {
    const totalAll = monthlyData.reduce((s,m) => s + (m.total || 0), 0);
    let chipsHtml = '<div class="month-chip ' + (selectedMonth === 'all' ? 'active' : '') + '" onclick="selectMonthChip(\'all\')">全部<span class="chip-count">' + totalAll + '</span></div>';
    for (const m of monthlyData) {
      const label = m.month.replace('-', '年') + '月';
      chipsHtml += '<div class="month-chip ' + (selectedMonth === m.month ? 'active' : '') + '" onclick="selectMonthChip(\'' + m.month + '\')">' + label + '<span class="chip-count">' + (m.total || 0) + '</span></div>';
    }
    chipsContainer.innerHTML = chipsHtml;
  }
  const displayData = selectedMonth === 'all' ? monthlyData : monthlyData.filter(m => m.month === selectedMonth);
  if (!displayData || displayData.length === 0) {
    container.innerHTML = '<div class="no-data">该月份暂无数据</div>';
    return;
  }

  let html = '';'''

if old_render in html:
    html = html.replace(old_render, new_render, 1)
    print('Replaced 2: renderMonthly with chips')
else:
    print('WARN: renderMonthly pattern not found')

# ========= 替换 3: renderMonthly 里的 for 循环变量名 =========
old_loop = "  for (const m of monthlyData) {\n    const monthLabel = m.month.replace('-', '年') + '月';"
new_loop = "  for (const m of displayData) {\n    const monthLabel = m.month.replace('-', '年') + '月';"
if old_loop in html:
    html = html.replace(old_loop, new_loop, 1)
    print('Replaced 3: for-loop var')
else:
    print('WARN: for-loop pattern not found')

# ========= 替换 4: 顶部全局变量 =========
old_var = "let currentTab = 'monthly';\nlet currentBank = '工商银行';\nlet currentSource = '';\nlet currentDateFrom = null;\nlet currentDateTo = null;\nlet monthlyData = [];"
new_var = "let currentTab = 'monthly';\nlet currentBank = '';\nlet currentSource = '';\nlet currentDateFrom = null;\nlet currentDateTo = null;\nlet monthlyData = [];\nlet selectedMonth = 'all';\nlet dailyMode = 'today';\nlet dailyDateFrom = null;\nlet dailyDateTo = null;"
if old_var in html:
    html = html.replace(old_var, new_var, 1)
    print('Replaced 4: globals')
else:
    print('WARN: globals pattern not found')

# ========= 替换 5: switchTab 函数 =========
old_switch = r'''function switchTab(tab) {
  currentTab = tab;
  document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
  event.target.classList.add('active');
  document.getElementById('monthlyView').style.display = tab === 'monthly' ? 'block' : 'none';
  document.getElementById('dailyView').classList.toggle('show', tab === 'daily');
  reloadData();
}'''

new_switch = r'''function switchTab(tab) {
  currentTab = tab;
  document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
  event.target.classList.add('active');
  document.getElementById('monthlyView').style.display = tab === 'monthly' ? 'block' : 'none';
  document.getElementById('dailyView').classList.toggle('show', tab === 'daily');
  document.getElementById('monthlyFilter').style.display = tab === 'monthly' ? 'flex' : 'none';
  document.getElementById('dailyFilter').style.display = tab === 'daily' ? 'flex' : 'none';
  if (tab === 'daily') initDailyDate();
  reloadData();
}

function selectMonthChip(month) {
  selectedMonth = month;
  renderMonthly();
}

function setDailyMode(mode) {
  dailyMode = mode;
  document.getElementById('modeToday').classList.toggle('active', mode === 'today');
  document.getElementById('modeRange').classList.toggle('active', mode === 'range');
  document.getElementById('dailyDateRange').style.display = mode === 'range' ? 'inline' : 'none';
  document.getElementById('dailyDateLabel').style.display = mode === 'range' ? 'inline' : 'none';
  initDailyDate();
  reloadData();
}

function initDailyDate() {
  if (dailyMode === 'today') {
    const today = new Date().toISOString().slice(0, 10);
    dailyDateFrom = today;
    dailyDateTo = today;
  } else {
    dailyDateFrom = document.getElementById('dailyDateFrom').value || null;
    dailyDateTo = document.getElementById('dailyDateTo').value || null;
  }
}'''

if old_switch in html:
    html = html.replace(old_switch, new_switch, 1)
    print('Replaced 5: switchTab')
else:
    print('WARN: switchTab pattern not found')

# ========= 替换 6: loadDaily =========
old_loadDaily = r'''async function loadDaily() {
  const params = new URLSearchParams();
  if (currentSource) params.set('source', currentSource);
  if (currentDateFrom) params.set('date_from', currentDateFrom);
  if (currentDateTo) params.set('date_to', currentDateTo);
  params.set('bank', '工商银行');
  const res = await fetch('/api/stats?' + params.toString());
  const stats = await res.json();
  const container = document.getElementById('bankCards');

  // Only show ICBC in daily view
  let banks = (stats.by_bank || []).filter(b => b.bank === '工商银行');'''

new_loadDaily = r'''async function loadDaily() {
  initDailyDate();
  const dailySource = document.getElementById('dailySourceFilter').value;
  const params = new URLSearchParams();
  if (dailySource) params.set('source', dailySource);
  if (dailyDateFrom) params.set('date_from', dailyDateFrom);
  if (dailyDateTo) params.set('date_to', dailyDateTo);
  params.set('bank', '工商银行');
  const res = await fetch('/api/stats?' + params.toString());
  const stats = await res.json();
  const container = document.getElementById('bankCards');

  // Only show ICBC in daily view
  let banks = (stats.by_bank || []).filter(b => b.bank === '工商银行');'''

if old_loadDaily in html:
    html = html.replace(old_loadDaily, new_loadDaily, 1)
    print('Replaced 6: loadDaily')
else:
    print('WARN: loadDaily pattern not found')

# ========= 替换 7: loadBankArticles 内的 source/date =========
old_loadBank = r'''  const params = new URLSearchParams();
  params.set('bank', bank);
  params.set('limit', '200');
  if (currentSource) params.set('source', currentSource);
  if (currentDateFrom) params.set('date_from', currentDateFrom);
  if (currentDateTo) params.set('date_to', currentDateTo);'''

new_loadBank = r'''  const params = new URLSearchParams();
  params.set('bank', bank);
  params.set('limit', '200');
  const dailySource = document.getElementById('dailySourceFilter').value;
  if (dailySource) params.set('source', dailySource);
  if (dailyDateFrom) params.set('date_from', dailyDateFrom);
  if (dailyDateTo) params.set('date_to', dailyDateTo);'''

if old_loadBank in html:
    html = html.replace(old_loadBank, new_loadBank, 1)
    print('Replaced 7: loadBankArticles')
else:
    print('WARN: loadBankArticles pattern not found')

with open(TEMPLATE, 'w', encoding='utf-8') as f:
    f.write(html)
print('Template updated.')
