import electron from 'electron'
import { mkdir, readFile, writeFile, rm } from 'node:fs/promises'
import path from 'node:path'

const AUTH_FILE_NAME = 'kugou-auth.json'
const { app } = electron

const authFilePath = () => path.join(app.getPath('userData'), AUTH_FILE_NAME)

export const readMusicAuthCookie = async () => {
  try {
    const raw = await readFile(authFilePath(), 'utf8')
    const parsed = JSON.parse(raw)
    return typeof parsed?.cookie === 'string' ? parsed.cookie : ''
  } catch (error) {
    if (error?.code === 'ENOENT') return ''
    throw error
  }
}

export const writeMusicAuthCookie = async (cookie) => {
  const filePath = authFilePath()
  await mkdir(path.dirname(filePath), { recursive: true })
  await writeFile(filePath, JSON.stringify({ cookie, updated_at: new Date().toISOString() }, null, 2), 'utf8')
}

export const clearMusicAuthCookie = async () => {
  try {
    await rm(authFilePath(), { force: true })
  } catch (error) {
    if (error?.code !== 'ENOENT') throw error
  }
}
