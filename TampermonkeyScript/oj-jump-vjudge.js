// ==UserScript==
// @name         AtCoder / Codeforces → VJudge + Luogu
// @namespace    https://vjudge.net/
// @version      1.1.0
// @description  在 AtCoder 和 Codeforces 题目页面左侧添加 VJudge / 洛谷 跳转按钮
// @match        https://atcoder.jp/contests/*
// @match        *://codeforces.com/*
// @match        *://*.codeforces.com/*
// @run-at       document-idle
// @grant        none
// ==/UserScript==

(function () {
  'use strict';

  if (document.getElementById('oj-jump-links')) return;

  const host = location.hostname;
  const path = location.pathname;

  /**
   * 解析当前页面，返回 { vjudge, luogu } 形式的题目 ID
   * @returns {{id: string, platform: 'AtCoder'|'CodeForces'} | null}
   */
  function parseProblem() {
    // 1. AtCoder
    // /contests/abc066/tasks/abc066_b  →  AtCoder-abc066_b / AT_abc066_b
    if (host === 'atcoder.jp') {
      const m = path.match(/^\/contests\/[^/]+\/tasks\/([^/]+)\/?$/);
      if (m) return { platform: 'AtCoder', id: m[1] };
    }

    // 2. Codeforces
    // /problemset/problem/443/B  |  /contest/443/problem/B
    // → CodeForces-443B / CF443B
    if (host === 'codeforces.com' || host.endsWith('.codeforces.com')) {
      const m =
        path.match(/^\/problemset\/problem\/(\d+)\/([A-Za-z][A-Za-z0-9]*)\/?$/) ||
        path.match(/^\/contest\/(\d+)\/problem\/([A-Za-z][A-Za-z0-9]*)\/?$/);
      if (m) return { platform: 'CodeForces', id: `${m[1]}${m[2]}` };
    }

    return null;
  }

  const problem = parseProblem();
  if (!problem) return;

  // 3. 各站点题目 ID 映射
  const luoguId =
    problem.platform === 'AtCoder' ? `AT_${problem.id}` : `CF${problem.id}`;

  const links = [
    {
      label: '↗ VJudge',
      href: `https://vjudge.net/problem/${problem.platform}-${problem.id}`,
      title: '在 VJudge 打开当前题目',
      color: '#2563eb',
      hover: '#1d4ed8'
    },
    {
      label: '↗ 洛谷',
      href: `https://www.luogu.com.cn/problem/${luoguId}`,
      title: '在洛谷打开当前题目',
      color: '#0e90d2',
      hover: '#0b7cb5'
    }
  ];

  // 4. 左侧垂直居中的容器
  const container = document.createElement('div');
  container.id = 'oj-jump-links';

  Object.assign(container.style, {
    position: 'fixed',
    left: '0',
    top: '50%',
    transform: 'translateY(-50%)',
    zIndex: '2147483647',
    display: 'flex',
    flexDirection: 'column',
    gap: '8px',
    opacity: '0.75',
    transition: 'opacity 0.15s ease'
  });

  container.addEventListener('mouseenter', () => {
    container.style.opacity = '1';
  });
  container.addEventListener('mouseleave', () => {
    container.style.opacity = '0.75';
  });

  // 5. 生成按钮
  for (const link of links) {
    const a = document.createElement('a');
    a.href = link.href;
    a.target = '_blank';
    a.rel = 'noopener noreferrer';
    a.textContent = link.label;
    a.title = link.title;

    Object.assign(a.style, {
      padding: '10px 16px',
      background: link.color,
      color: '#ffffff',
      borderRadius: '0 8px 8px 0',
      fontSize: '14px',
      fontWeight: 'bold',
      fontFamily: 'Arial, sans-serif',
      textDecoration: 'none',
      whiteSpace: 'nowrap',
      boxShadow: '0 4px 12px rgba(0,0,0,0.2)',
      cursor: 'pointer'
    });

    a.addEventListener('mouseenter', () => {
      a.style.background = link.hover;
    });
    a.addEventListener('mouseleave', () => {
      a.style.background = link.color;
    });

    container.appendChild(a);
  }

  document.body.appendChild(container);
})();
