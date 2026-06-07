import { createHash } from 'node:crypto'
import { readFile, writeFile, mkdir } from 'node:fs/promises'
import { existsSync } from 'node:fs'
import { join } from 'node:path'
import { homedir, tmpdir } from 'node:os'
import { CACHE_TTL_MS } from '../constants.mjs'

const CACHE_DIR = join(homedir(), '.squirrel', 'playback-cache')

const getCacheFilePath = (cacheKey) => {
  const hash = createHash('sha1').update(cacheKey).digest('hex')
  return join(CACHE_DIR, `${hash}.json`)
}

const ensureCacheDir = async () => {
  if (!existsSync(CACHE_DIR)) {
    await mkdir(CACHE_DIR, { recursive: true })
  }
}

export const loadFileCache = async (cacheKey, ttlMs = CACHE_TTL_MS) => {
  try {
    await ensureCacheDir()
    const filePath = getCacheFilePath(cacheKey)
    const raw = await readFile(filePath, 'utf-8')
    const entry = JSON.parse(raw)
    if (entry.expiresAt <= Date.now()) {
      return null
    }
    return entry.value
  } catch (err) {
    console.debug('[squirrel-desktop] file-cache load error', err)
    return null
  }
}

export const saveFileCache = async (cacheKey, value, ttlMs = CACHE_TTL_MS) => {
  try {
    await ensureCacheDir()
    const filePath = getCacheFilePath(cacheKey)
    const entry = { value, expiresAt: Date.now() + ttlMs }
    await writeFile(filePath, JSON.stringify(entry), 'utf-8')
  } catch (err) {
    console.debug('[squirrel-desktop] file-cache save error', err)
  }
}
