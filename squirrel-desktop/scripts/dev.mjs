import { spawn } from 'node:child_process'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import chokidar from 'chokidar'

const __filename = fileURLToPath(import.meta.url)
const __dirname = path.dirname(__filename)

const desktopDir = path.resolve(__dirname, '..')
const frontendDir = path.resolve(desktopDir, '..', 'squirrel-frontend')
const desktopSrcDir = path.resolve(desktopDir, 'src')

const npmCmd = process.platform === 'win32' ? 'npm.cmd' : 'npm'
const backendUrl = String(process.env.VITE_BACKEND_URL || 'http://127.0.0.1:8001').trim()
const rendererUrl = String(process.env.DESKTOP_RENDERER_URL || 'http://127.0.0.1:5173').trim()
const rendererPort = String(new URL(rendererUrl).port || '5173')
const shouldUseShell = process.platform === 'win32'

let frontendProcess = null
let electronProcess = null
let desktopWatcher = null
let restartTimer = null
let restartingElectron = false
let lastRestartAt = 0
let shuttingDown = false
let shutdownPromise = null
let electronStartupAt = 0
let restartCount = 0
let restartCountResetTimer = null

const MAX_RESTARTS_PER_WINDOW = 5
const RESTART_COUNT_WINDOW_MS = 30000

const wait = (ms) => new Promise((resolve) => setTimeout(resolve, ms))

const waitForProcessExit = (child, timeoutMs = 5000) => {
  if (!child || child.exitCode !== null) {
    return Promise.resolve()
  }

  return new Promise((resolve) => {
    let settled = false
    let timeout = null

    const finish = () => {
      if (settled) {
        return
      }

      settled = true
      if (timeout) {
        clearTimeout(timeout)
      }
      resolve()
    }

    child.once('exit', finish)
    child.once('error', finish)
    timeout = setTimeout(finish, timeoutMs)
  })
}

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

const terminate = async (child) => {
  if (!child || child.exitCode !== null) {
    return
  }

  if (process.platform === 'win32') {
    await new Promise((resolve) => {
      const killer = spawn(
        'taskkill',
        ['/pid', String(child.pid), '/t', '/f'],
        {
          stdio: 'ignore',
          windowsHide: true,
        }
      )

      killer.once('exit', resolve)
      killer.once('error', resolve)
    })

    await waitForProcessExit(child, 5000)
    return
  }

  child.kill('SIGTERM')
  await waitForProcessExit(child, 3000)

  if (child.exitCode === null) {
    child.kill('SIGKILL')
    await waitForProcessExit(child, 2000)
  }
}

const spawnNpm = (args, options) => {
  return spawn(npmCmd, args, {
    ...options,
    shell: shouldUseShell,
  })
}

const shutdown = (exitCode = 0) => {
  if (shutdownPromise) {
    return shutdownPromise
  }

  shuttingDown = true
  shutdownPromise = (async () => {
    if (desktopWatcher) {
      desktopWatcher.close()
      desktopWatcher = null
    }
    if (restartTimer) {
      clearTimeout(restartTimer)
      restartTimer = null
    }
    if (restartCountResetTimer) {
      clearTimeout(restartCountResetTimer)
      restartCountResetTimer = null
    }
    await Promise.allSettled([
      terminate(electronProcess),
      terminate(frontendProcess),
    ])
    process.exit(exitCode)
  })()

  return shutdownPromise
}

const startElectron = () => {
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

  electronStartupAt = Date.now()

  electronProcess.on('exit', (code) => {
    electronProcess = null
    if (shuttingDown || restartingElectron) {
      return
    }

    void shutdown(code ?? 0)
  })
}

const restartElectron = async () => {
  if (shuttingDown || restartingElectron) {
    return
  }

  restartCount += 1
  if (!restartCountResetTimer) {
    restartCountResetTimer = setTimeout(() => {
      restartCount = 0
      restartCountResetTimer = null
    }, RESTART_COUNT_WINDOW_MS)
  }

  if (restartCount > MAX_RESTARTS_PER_WINDOW) {
    console.error(
      `[squirrel-desktop] Too many restarts (${restartCount}) in ${RESTART_COUNT_WINDOW_MS / 1000}s — stopping auto-restart. ` +
      'Restart the dev script manually to resume.'
    )
    return
  }

  restartingElectron = true
  console.log('[squirrel-desktop] Desktop source changed, restarting Electron')
  await terminate(electronProcess)
  electronProcess = null
  startElectron()
  lastRestartAt = Date.now()
  restartingElectron = false
}

const RESTART_DEBOUNCE_MS = 500
const RESTART_COOLDOWN_MS = 5000
const RESTART_GRACE_PERIOD_MS = 10000

const scheduleElectronRestart = () => {
  if (restartingElectron) {
    return
  }

  if (lastRestartAt && Date.now() - lastRestartAt < RESTART_COOLDOWN_MS) {
    return
  }

  // Ignore fs.watch events during the startup grace period — on Windows, the
  // filesystem watcher may fire false positives while Electron initializes,
  // and prewarming operations (YouTube InnerTube cache, JavDB Cloudflare
  // document loading) or background OS activity can trigger spurious events
  // that would otherwise cause a restart loop.
  if (electronStartupAt && Date.now() - electronStartupAt < RESTART_GRACE_PERIOD_MS) {
    return
  }

  if (restartTimer) {
    clearTimeout(restartTimer)
  }
  restartTimer = setTimeout(() => {
    restartTimer = null
    void restartElectron()
  }, RESTART_DEBOUNCE_MS)
}

const watchDesktopSource = () => {
  desktopWatcher = chokidar.watch('**/*.{cjs,mjs,js,json}', {
    cwd: desktopSrcDir,
    ignoreInitial: true,
    awaitWriteFinish: {
      stabilityThreshold: 200,
      pollInterval: 50,
    },
  })

  desktopWatcher.on('all', (eventType, changedFile) => {
    console.debug(`[squirrel-desktop] source ${eventType}: ${changedFile}`)
    scheduleElectronRestart()
  })
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
      void shutdown(code ?? 1)
    }
  })

  await waitForServer(rendererUrl)

  startElectron()
  watchDesktopSource()
}

process.on('SIGINT', () => {
  void shutdown(0)
})
process.on('SIGTERM', () => {
  void shutdown(0)
})

start().catch((error) => {
  console.error('[squirrel-desktop] Failed to start dev mode', error)
  void shutdown(1)
})
