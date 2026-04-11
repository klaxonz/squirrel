import { spawn } from 'node:child_process'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const __filename = fileURLToPath(import.meta.url)
const __dirname = path.dirname(__filename)

const desktopDir = path.resolve(__dirname, '..')
const frontendDir = path.resolve(desktopDir, '..', 'squirrel-frontend')

const npmCmd = process.platform === 'win32' ? 'npm.cmd' : 'npm'
const backendUrl = String(process.env.VITE_BACKEND_URL || 'http://127.0.0.1:8001').trim()
const rendererUrl = String(process.env.DESKTOP_RENDERER_URL || 'http://127.0.0.1:5173').trim()
const rendererPort = String(new URL(rendererUrl).port || '5173')
const shouldUseShell = process.platform === 'win32'

let frontendProcess = null
let electronProcess = null
let shuttingDown = false

const wait = (ms) => new Promise((resolve) => setTimeout(resolve, ms))

const waitForServer = async (url, timeoutMs = 60000) => {
  const startedAt = Date.now()

  while (Date.now() - startedAt < timeoutMs) {
    try {
      const response = await fetch(url, { method: 'GET' })
      if (response.ok || response.status === 404) {
        return
      }
    } catch {
      // Retry until the timeout is hit.
    }

    await wait(500)
  }

  throw new Error(`Timed out waiting for renderer server: ${url}`)
}

const terminate = (child) => {
  if (!child || child.killed) {
    return
  }

  child.kill('SIGTERM')
}

const spawnNpm = (args, options) => {
  return spawn(npmCmd, args, {
    ...options,
    shell: shouldUseShell,
  })
}

const shutdown = (exitCode = 0) => {
  if (shuttingDown) {
    return
  }

  shuttingDown = true
  terminate(electronProcess)
  terminate(frontendProcess)
  process.exit(exitCode)
}

const start = async () => {
  frontendProcess = spawnNpm(
    ['run', 'dev', '--', '--host', '127.0.0.1', '--port', rendererPort],
    {
      cwd: frontendDir,
      env: {
        ...process.env,
        VITE_BACKEND_URL: backendUrl,
      },
      stdio: 'inherit',
    }
  )

  frontendProcess.on('exit', (code) => {
    if (!shuttingDown) {
      shutdown(code ?? 1)
    }
  })

  await waitForServer(rendererUrl)

  electronProcess = spawnNpm(
    ['run', 'start'],
    {
      cwd: desktopDir,
      env: {
        ...process.env,
        DESKTOP_RENDERER_URL: rendererUrl,
        DESKTOP_APP_URL: backendUrl,
      },
      stdio: 'inherit',
    }
  )

  electronProcess.on('exit', (code) => {
    shutdown(code ?? 0)
  })
}

process.on('SIGINT', () => shutdown(0))
process.on('SIGTERM', () => shutdown(0))

start().catch((error) => {
  console.error('[squirrel-desktop] Failed to start dev mode', error)
  shutdown(1)
})
