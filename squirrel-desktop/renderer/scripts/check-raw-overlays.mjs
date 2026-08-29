import fs from 'node:fs/promises'
import path from 'node:path'

// Lint gate: custom floating surfaces in feature code are forbidden.
// Overlays must use the shared primitives — Dialog (modal), Popover /
// DropdownMenu (anchored), Tooltip (annotation). Raw `Teleport` +
// `position: fixed` stacks re-implement stacking, focus, and dismissal
// per-feature and drift from the --z-* scale.
//
// Declared whitelist (docs/ui-system-consolidation-plan.md, Phase 2):
// each entry is a surface the primitives genuinely don't cover — fullscreen
// media, non-modal toasts, or shared overlay infrastructure itself.
const WHITELIST = [
  // Shared overlay infrastructure — defines the system, not a bypass.
  'shared/components/toast/ToastProvider.vue',
  'shared/components/layout/AppContextMenu.vue',
  // Docked / fixed chrome layout (not floating surfaces).
  'features/music/components/GlobalMusicPlayerBar.vue',
  'shared/components/ServerStatusButton.vue',
  // Fullscreen media surfaces (z-player-overlay tier).
  'features/playback/components/video-player/GlobalVideoPlayerHost.vue',
  'features/music/components/player/MusicImmersivePlayer.vue',
  // Fullscreen image lightbox — zoom UX, not a modal dialog.
  'features/rss/components/RssImageLightbox.vue',
  // Non-modal toast-tier banner (device-code OAuth prompt).
  'features/settings/components/YouTubeOAuthPrompt.vue',
  // In-player hover preview / chapter UI (player sub-theme scope).
  'features/video/components/feed/VideoItem.vue',
]

const PROJECT_ROOT = path.resolve(process.cwd(), 'renderer')
const TARGET_ROOT = path.join(PROJECT_ROOT, 'src')
const RAW_OVERLAY_RE = /Teleport|position:\s*fixed/

async function walk(dir) {
  const entries = await fs.readdir(dir, { withFileTypes: true })
  const files = []
  for (const entry of entries) {
    const full = path.join(dir, entry.name)
    if (entry.isDirectory()) files.push(...(await walk(full)))
    else if (entry.name.endsWith('.vue')) files.push(full)
  }
  return files
}

const violations = []
for (const file of await walk(TARGET_ROOT)) {
  const rel = path.relative(path.join(PROJECT_ROOT, 'src'), file).replace(/\\/g, '/')
  if (WHITELIST.includes(rel)) continue
  const source = await fs.readFile(file, 'utf8')
  const lines = source.split('\n')
  lines.forEach((line, i) => {
    if (RAW_OVERLAY_RE.test(line)) {
      violations.push(`src/${rel}:${i + 1}: ${line.trim()}`)
    }
  })
}

if (violations.length) {
  console.error(
    `raw overlay usage found (${violations.length}) — use shared/ui Dialog, Popover,\n` +
    `DropdownMenu, or Tooltip instead. To add a legitimate exception, extend\n` +
    `the WHITELIST in this script with a justification:\n\n`,
  )
  for (const v of violations) console.error('  ' + v)
  process.exit(1)
}
console.log('check-raw-overlays: OK')
