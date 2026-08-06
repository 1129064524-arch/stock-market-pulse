const { spawnSync } = require('node:child_process')
const fs = require('node:fs')
const path = require('node:path')

const projectRoot = path.resolve(__dirname, '..')
const candidates = process.platform === 'win32'
  ? [
      { command: path.join(projectRoot, '.venv', 'Scripts', 'python.exe'), args: [] },
      { command: 'python', args: [] },
      { command: 'py', args: ['-3'] },
    ]
  : [
      { command: path.join(projectRoot, '.venv', 'bin', 'python'), args: [] },
      { command: 'python3', args: [] },
      { command: 'python', args: [] },
    ]

const args = process.argv.slice(2)
for (const candidate of candidates) {
  if (path.isAbsolute(candidate.command) && !fs.existsSync(candidate.command)) continue
  const result = spawnSync(candidate.command, [...candidate.args, ...args], {
    cwd: projectRoot,
    stdio: 'inherit',
    windowsHide: false,
  })
  if (result.error?.code === 'ENOENT') continue
  process.exit(result.status ?? 1)
}

console.error('找不到可用的 Python 解释器，请安装 Python 3.12 或创建项目虚拟环境。')
process.exit(1)
