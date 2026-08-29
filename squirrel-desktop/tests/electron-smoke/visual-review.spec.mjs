import fs from 'node:fs/promises'
import path from 'node:path'

const root = path.resolve(process.env.VISUAL_REVIEW_OUT ?? 'visual-review-results')
const candidate = path.join(root, 'candidate')

export async function collectElectronEvidence() {
  await fs.mkdir(candidate, { recursive: true })
  await browser.saveScreenshot(path.join(candidate, 'actual.png'))
  const evidence = await browser.execute(() => {
    const visible = [...document.querySelectorAll('body *')].filter((el) => {
      const r = el.getBoundingClientRect(); const s = getComputedStyle(el)
      return r.width > 0 && r.height > 0 && s.visibility !== 'hidden'
    }).slice(0, 200)
    return {
      source: 'electron-wdio', provenance: { mode: 'electron', target: 'business' },
      viewport: { width: innerWidth, height: innerHeight, deviceScaleFactor: devicePixelRatio, overflow: { horizontal: document.documentElement.scrollWidth > innerWidth, vertical: document.documentElement.scrollHeight > innerHeight } },
      aria: { title: document.title, role: document.body.getAttribute('role'), name: document.body.getAttribute('aria-label') },
      accessibility: visible.map((el) => ({ selector: el.tagName.toLowerCase(), role: el.getAttribute('role'), accessibleName: el.getAttribute('aria-label') || el.textContent?.trim().slice(0, 120) || '' })),
      styles: visible.map((el) => { const s = getComputedStyle(el); return { selector: el.tagName.toLowerCase(), display: s.display, color: s.color, backgroundColor: s.backgroundColor, fontSize: s.fontSize } }),
      rawStyles: [], console: window.__visualConsole ?? [], unhandledRejections: window.__visualRejections ?? [], taskTrace: window.__taskTrace ?? { status: 'blocked', steps: [] },
    }
  })
  for (const [file, value] of [['dom.json', evidence.aria], ['styles.json', evidence.styles], ['task-trace.json', evidence.taskTrace]]) await fs.writeFile(path.join(candidate, file), JSON.stringify(value, null, 2))
  await fs.writeFile(path.join(candidate, 'evidence.json'), JSON.stringify(evidence, null, 2))
}

describe('Electron visual review collector', () => {
  it('captures renderer evidence without network', async () => {
    await browser.waitUntil(async () => (await browser.getTitle()) === 'Squirrel Electron Smoke', { timeout: 30_000 })
    await collectElectronEvidence()
  })
})
