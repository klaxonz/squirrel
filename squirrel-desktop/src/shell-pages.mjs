import { APP_NAME } from './constants.mjs'

let rendererUrl = ''

export const setRendererUrl = (url) => {
  rendererUrl = url
}

const escapeHtml = (value) => {
  return String(value ?? '')
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#39;')
}

export const formatWindowTitle = (value) => {
  const title = String(value || '').trim()
  if (!title || title === APP_NAME) {
    return APP_NAME
  }

  return title.endsWith(` - ${APP_NAME}`) ? title : `${title} - ${APP_NAME}`
}

const buildShellPageUrl = ({ title, eyebrow, heading, body, status, tone = 'loading' }) => {
  const accent = tone === 'error' ? '#f97373' : '#7dd3fc'
  const actionScript = `window.desktopApp?.reloadApp?.() || window.location.replace(${JSON.stringify(rendererUrl)})`
  const openExternalScript = `window.desktopApp?.openExternal?.(${JSON.stringify(rendererUrl)}) || window.open(${JSON.stringify(rendererUrl)}, '_blank', 'noopener,noreferrer')`

  const html = `<!doctype html>
<html lang="zh-CN">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>${escapeHtml(formatWindowTitle(title))}</title>
    <style>
      :root {
        color-scheme: dark;
        --bg: #05080c;
        --panel: rgba(12, 18, 26, 0.88);
        --panel-border: rgba(125, 211, 252, 0.16);
        --text: rgba(255, 255, 255, 0.94);
        --muted: rgba(255, 255, 255, 0.62);
        --accent: ${accent};
      }
      * { box-sizing: border-box; }
      body {
        margin: 0;
        min-height: 100vh;
        display: grid;
        place-items: center;
        overflow: hidden;
        background:
          radial-gradient(circle at top, rgba(125, 211, 252, 0.12), transparent 36%),
          radial-gradient(circle at bottom right, rgba(56, 189, 248, 0.08), transparent 24%),
          linear-gradient(180deg, #08111a 0%, var(--bg) 100%);
        color: var(--text);
        font-family: "Segoe UI", "PingFang SC", "Microsoft YaHei", sans-serif;
      }
      .shell {
        width: min(36rem, calc(100vw - 2rem));
        padding: 1.5rem;
        border-radius: 1.25rem;
        border: 1px solid var(--panel-border);
        background: var(--panel);
        backdrop-filter: blur(18px);
        box-shadow: 0 24px 80px rgba(0, 0, 0, 0.38);
      }
      .eyebrow {
        margin: 0 0 0.75rem;
        color: var(--accent);
        font-size: 0.78rem;
        letter-spacing: 0.18em;
        text-transform: uppercase;
      }
      h1 {
        margin: 0;
        font-size: clamp(1.5rem, 4vw, 2.15rem);
        line-height: 1.1;
      }
      p {
        margin: 0;
        font-size: 0.98rem;
        line-height: 1.7;
        color: var(--muted);
      }
      .copy {
        display: grid;
        gap: 0.9rem;
      }
      .status {
        margin-top: 1.2rem;
        padding: 0.8rem 0.95rem;
        border-radius: 0.85rem;
        background: rgba(255, 255, 255, 0.04);
        border: 1px solid rgba(255, 255, 255, 0.06);
        color: var(--muted);
        font-family: "JetBrains Mono", Consolas, monospace;
        font-size: 0.82rem;
        word-break: break-all;
      }
      .actions {
        display: flex;
        flex-wrap: wrap;
        gap: 0.75rem;
        margin-top: 1.2rem;
      }
      button, a {
        appearance: none;
        border: 0;
        cursor: pointer;
        border-radius: 999px;
        padding: 0.8rem 1.15rem;
        font: inherit;
        text-decoration: none;
      }
      .primary {
        background: linear-gradient(135deg, var(--accent), #38bdf8);
        color: #04121e;
        font-weight: 700;
      }
      .secondary {
        background: rgba(255, 255, 255, 0.06);
        color: var(--text);
      }
    </style>
  </head>
  <body>
    <main class="shell">
      <div class="copy">
        <div class="eyebrow">${escapeHtml(eyebrow)}</div>
        <h1>${escapeHtml(heading)}</h1>
        <p>${escapeHtml(body)}</p>
      </div>
      <div class="status">${escapeHtml(status)}</div>
      <div class="actions">
        <button class="primary" type="button" onclick="${actionScript}">重试连接</button>
        <button class="secondary" type="button" onclick="${openExternalScript}">浏览器打开</button>
      </div>
    </main>
  </body>
</html>`

  return `data:text/html;charset=UTF-8,${encodeURIComponent(html)}`
}

export const showErrorShell = (mainWindow, details) => {
  const errorSummary = [
    rendererUrl,
    details?.errorCode ? `code=${details.errorCode}` : null,
    details?.errorDescription || null,
  ].filter(Boolean).join('\n')

  return mainWindow.loadURL(buildShellPageUrl({
    title: '连接失败',
    eyebrow: 'Desktop Recovery',
    heading: '页面入口暂时不可用',
    body: '桌面壳已经启动，但还没有连接上前端页面。请确认前端地址可访问，或直接点击重试。',
    status: errorSummary,
    tone: 'error',
  }))
}
