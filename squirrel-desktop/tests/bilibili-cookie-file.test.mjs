import assert from 'node:assert/strict'
import test from 'node:test'
import { mkdtemp, rm, writeFile } from 'node:fs/promises'
import os from 'node:os'
import path from 'node:path'
import {
  hasCookieName,
  mergeBilibiliFileCookieFallback,
  parseNetscapeCookieFile,
  readBilibiliCookieFileHeader,
} from '../src/bilibili-cookie-file.mjs'

const SAMPLE_COOKIE_FILE = `# Netscape HTTP Cookie File
.bilibili.com\tTRUE\t/\tFALSE\t1793455639\tbuvid3\tB8108BB6-440D-6A09-32BD-3358548593CE37705infoc
.bilibili.com\tTRUE\t/\tFALSE\t1793455639\tb_nut\t1761919637
.bilibili.com\tTRUE\t/\tTRUE\t1799147154\tDedeUserID\t20324829
#HttpOnly_.bilibili.com\tTRUE\t/\tTRUE\t1799147154\tSESSDATA\t92fa4949%2C1799147153%2C32423%2A71CjC54XEPdZllj9L5VXEJxOOdp7wcv8oK3iI29JuQBtyMgZtL0vdI6zHuSJquPXDr-DcSVkFXV25lQkF2NmNHeHM4MjhWYjVhZ2RreHZFcFRfQ1ZUcjk4cEpmTXVsZVBkTU9ONTktcGtUVDlyNHdQRGk3NnYySmpkWlhzSVBxeVpSMUVZTGxvOHNnIIEC
.bilibili.com\tTRUE\t/\tTRUE\t1799147154\tbili_jct\t26c9b5965bf0fb2b21e52f2e325e4522
.bilibili.com\tTRUE\t/\tFALSE\t0\tb_lsid\t28627A54_19F50AB61F0
.youtube.com\tTRUE\t/\tFALSE\t1799999999\tSID\tstray-not-bilibili
# a pure comment line
$

http://malformed.without.tabs
`

const withTempCookieFile = async (content, fn) => {
  const dir = await mkdtemp(path.join(os.tmpdir(), 'squirrel-bili-cookies-'))
  const filePath = path.join(dir, 'bilibili.txt')
  try {
    await writeFile(filePath, content, 'utf8')
    return await fn(filePath)
  } finally {
    await rm(dir, { recursive: true, force: true })
  }
}

test('parseNetscapeCookieFile mirrors backend MozillaCookieJar line rules', () => {
  const cookies = parseNetscapeCookieFile(SAMPLE_COOKIE_FILE)
  const names = cookies.map((cookie) => cookie.name)

  // HttpOnly SESSDATA line is a real cookie, not a comment.
  assert.ok(names.includes('SESSDATA'))
  assert.ok(names.includes('buvid3'))
  assert.ok(names.includes('bili_jct'))
  assert.ok(names.includes('b_lsid'))
  // Parsing is domain-agnostic (like MozillaCookieJar); the bilibili-only
  // domain filter is applied when building the header (next test).
  assert.ok(names.includes('SID'))
  assert.ok(cookies.length === 7, `expected 7 parsed cookies, got ${cookies.length}`)

  const sessdata = cookies.find((cookie) => cookie.name === 'SESSDATA')
  assert.equal(sessdata.domain, '.bilibili.com')
  assert.equal(sessdata.secure, true)
  assert.equal(sessdata.domainSpecified, true)
  assert.match(sessdata.value, /^92fa4949/)

  const bLsid = cookies.find((cookie) => cookie.name === 'b_lsid')
  assert.equal(bLsid.expires, 0, 'expiry 0 kept (backend loads with ignore_expires=True)')
})

test('readBilibiliCookieFileHeader builds header and filters to bilibili domain', async () => {
  await withTempCookieFile(SAMPLE_COOKIE_FILE, async (filePath) => {
    const header = await readBilibiliCookieFileHeader({ filePath })

    assert.match(header, /SESSDATA=92fa4949/)
    assert.match(header, /buvid3=B8108BB6/)
    assert.match(header, /bili_jct=26c9b596/)
    assert.doesNotMatch(header, /SID=stray-not-bilibili/, 'youtube.com cookies must not leak into the header')
    assert.doesNotMatch(header, /^\s*$/)
  })
})

test('readBilibiliCookieFileHeader returns empty string for missing file', async () => {
  assert.equal(
    await readBilibiliCookieFileHeader({ filePath: path.join(os.tmpdir(), 'definitely-missing-cookies.txt') }),
    '',
  )
})

test('mergeBilibiliFileCookieFallback keeps session untouched when it has SESSDATA', async () => {
  const sessionHeader = 'SESSDATA=session-value; buvid3=session-buvid'
  // Bogus filePath proves the file is not even read when session is signed in.
  const merged = await mergeBilibiliFileCookieFallback(sessionHeader, {
    filePath: path.join(os.tmpdir(), 'never-read.txt'),
  })
  assert.equal(merged, sessionHeader)
})

test('mergeBilibiliFileCookieFallback reads the file when session is anonymous', async () => {
  await withTempCookieFile(SAMPLE_COOKIE_FILE, async (filePath) => {
    const merged = await mergeBilibiliFileCookieFallback('buvid3=anon-session-buvid', { filePath })

    // File SESSDATA is the whole point of the fallback.
    assert.match(merged, /SESSDATA=92fa4949/)
    // Session value wins on collision with the file.
    assert.match(merged, /buvid3=anon-session-buvid/)
    assert.doesNotMatch(merged, /buvid3=B8108BB6/)
    // File fills gaps the session does not have.
    assert.match(merged, /bili_jct=26c9b596/)
    assert.match(merged, /b_lsid=28627A54/)
  })
})

test('mergeBilibiliFileCookieFallback returns session header when file is missing', async () => {
  const sessionHeader = 'buvid3=anon-session-buvid'
  const merged = await mergeBilibiliFileCookieFallback(sessionHeader, {
    filePath: path.join(os.tmpdir(), 'definitely-missing-cookies.txt'),
  })
  assert.equal(merged, sessionHeader)
})

test('hasCookieName matches leading and separated cookie names only', () => {
  assert.equal(hasCookieName('SESSDATA=abc', 'SESSDATA'), true)
  assert.equal(hasCookieName('buvid3=x; SESSDATA=abc', 'SESSDATA'), true)
  assert.equal(hasCookieName('buvid3=x; SESSDATA=abc; b_nut=y', 'SESSDATA'), true)
  assert.equal(hasCookieName('buvid3=x', 'SESSDATA'), false)
  assert.equal(hasCookieName('SESSDATAx=abc', 'SESSDATA'), false)
  assert.equal(hasCookieName('', 'SESSDATA'), false)
  assert.equal(hasCookieName('buvid3=x', ''), false)
})
