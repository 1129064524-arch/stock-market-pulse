const { app, BrowserWindow, dialog } = require('electron')
const { autoUpdater } = require('electron-updater')
const { spawn } = require('node:child_process')
const fs = require('node:fs')
const path = require('node:path')
const http = require('node:http')

const API_PORT = Number(process.env.MARKET_PULSE_API_PORT || 8765)
let backendProcess

function backendExecutable() {
  const binaryName = process.platform === 'win32' ? 'market-pulse-api.exe' : 'market-pulse-api'
  if (process.env.MARKET_PULSE_API_EXECUTABLE) return process.env.MARKET_PULSE_API_EXECUTABLE
  return path.join(process.resourcesPath, 'backend', binaryName)
}

function startBackend() {
  if (!app.isPackaged && !process.env.MARKET_PULSE_API_EXECUTABLE) return
  const executable = backendExecutable()
  if (!fs.existsSync(executable)) throw new Error(`找不到本地 API：${executable}`)
  const userData = app.getPath('userData')
  const configPath = path.join(userData, '.env')
  backendProcess = spawn(executable, [], {
    cwd: userData,
    env: {
      ...process.env,
      MARKET_PULSE_API_PORT: String(API_PORT),
      MARKET_PULSE_WEB_ROOT: path.join(process.resourcesPath, 'web'),
      MARKET_DB_PATH: path.join(userData, 'data', 'market-pulse.sqlite3'),
      MARKET_PULSE_CONFIG_PATH: configPath,
      DOTENV_CONFIG_PATH: configPath,
    },
    windowsHide: true,
    stdio: 'ignore',
  })
  backendProcess.on('error', (error) => console.error('Market Pulse API failed:', error))
}

function waitForBackend(timeoutMs = 15000) {
  const startedAt = Date.now()
  return new Promise((resolve, reject) => {
    const check = () => {
      const request = http.get(`http://127.0.0.1:${API_PORT}/api/health`, (response) => {
        response.resume()
        if (response.statusCode === 200) return resolve()
        retry()
      })
      request.on('error', retry)
      request.setTimeout(1000, () => request.destroy())
    }
    const retry = () => {
      if (Date.now() - startedAt > timeoutMs) reject(new Error('本地 API 启动超时'))
      else setTimeout(check, 250)
    }
    check()
  })
}

async function createWindow() {
  const window = new BrowserWindow({
    width: 1440,
    height: 920,
    minWidth: 1180,
    minHeight: 720,
    backgroundColor: '#f4f1ec',
    webPreferences: { contextIsolation: true, nodeIntegration: false },
  })
  const startUrl = process.env.ELECTRON_START_URL || (app.isPackaged
    ? `http://127.0.0.1:${API_PORT}/app/`
    : 'http://127.0.0.1:4175/')
  await window.loadURL(startUrl)
  return window
}

app.whenReady().then(async () => {
  try {
    startBackend()
    if (app.isPackaged || process.env.MARKET_PULSE_API_EXECUTABLE) await waitForBackend()
    await createWindow()
    if (app.isPackaged) {
      autoUpdater.checkForUpdatesAndNotify().catch((error) => console.warn('Update check failed:', error.message))
    }
  } catch (error) {
    dialog.showErrorBox('Market Pulse 启动失败', error.message)
    app.quit()
  }
})

app.on('window-all-closed', () => {
  if (backendProcess && !backendProcess.killed) backendProcess.kill()
  if (process.platform !== 'darwin') app.quit()
})

app.on('before-quit', () => {
  if (backendProcess && !backendProcess.killed) backendProcess.kill()
})
