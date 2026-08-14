#!/usr/bin/env node

const { execSync } = require('child_process')
const fs = require('fs')
const path = require('path')

const PROJECT_ROOT = path.resolve(__dirname, '..')

function run(cmd, opts = {}) {
  try { return execSync(cmd, { cwd: PROJECT_ROOT, encoding: 'utf8', stdio: 'pipe', ...opts }).trim() }
  catch (e) { return null }
}

function status() {
  console.log('=== WhatsApp Bridge Status ===\n')
  
  const git = run('git status --short')
  const branch = run('git branch --show-current')
  const commit = run('git log -1 --oneline')
  
  console.log('Git branch:', branch || 'none')
  console.log('Last commit:', commit || 'none')
  console.log('Changes:', git ? git.split('\n').length : 0)
  
  const pkg = JSON.parse(fs.readFileSync(path.join(PROJECT_ROOT, 'package.json'), 'utf8'))
  console.log('Version:', pkg.version)
  console.log('Node engines:', pkg.engines?.node || 'not specified')
  
  const envExists = fs.existsSync(path.join(PROJECT_ROOT, '.env'))
  const envExampleExists = fs.existsSync(path.join(PROJECT_ROOT, '.env.example'))
  console.log('.env exists:', envExists)
  console.log('.env.example exists:', envExampleExists)
  
  const botExists = fs.existsSync(path.join(PROJECT_ROOT, 'bot.js'))
  console.log('bot.js exists:', botExists)
  
  const logsDir = path.join(PROJECT_ROOT, 'logs')
  const logs = fs.existsSync(logsDir) ? fs.readdirSync(logsDir).length : 0
  console.log('Log files:', logs)
}

function analyze() {
  console.log('=== WhatsApp Bridge Analysis ===\n')
  
  const issues = []
  
  if (!fs.existsSync(path.join(PROJECT_ROOT, '.env.example'))) {
    issues.push({ priority: 'critical', issue: 'Missing .env.example', fix: 'Create .env.example with placeholder values' })
  }
  
  const pkg = JSON.parse(fs.readFileSync(path.join(PROJECT_ROOT, 'package.json'), 'utf8'))
  if (!pkg.scripts?.start) {
    issues.push({ priority: 'high', issue: 'No start script in package.json', fix: 'Add "start": "node bot.js"' })
  }
  
  if (!fs.existsSync(path.join(PROJECT_ROOT, 'src'))) {
    issues.push({ priority: 'medium', issue: 'No src/ directory', fix: 'Organize code into src/' })
  }
  
  const buildResult = run('npm run lint')
  if (buildResult === null) {
    issues.push({ priority: 'medium', issue: 'Linting not configured', fix: 'Add oxlint or eslint' })
  }
  
  console.log(`Issues found: ${issues.length}\n`)
  issues.forEach((issue, i) => {
    console.log(`${i + 1}. [${issue.priority.toUpperCase()}] ${issue.issue}`)
    console.log(`   Fix: ${issue.fix}\n`)
  })
}

function improve() {
  console.log('=== Improvement Suggestions ===\n')
  
  const suggestions = [
    { priority: 'high', action: 'Add PM2 ecosystem file', reason: 'Better process management than batch files' },
    { priority: 'high', action: 'Add health check endpoint', reason: 'Enable monitoring and auto-restart' },
    { priority: 'medium', action: 'Add input validation', reason: 'Prevent malformed WhatsApp messages from crashing the bot' },
    { priority: 'medium', action: 'Add rate limiting', reason: 'Prevent abuse of the WhatsApp bridge' },
    { priority: 'medium', action: 'Add structured logging', reason: 'Replace console.log with a proper logger' },
    { priority: 'low', action: 'Add Docker support', reason: 'Easier deployment and scaling' },
  ]
  
  suggestions.forEach((s, i) => {
    console.log(`${i + 1}. [${s.priority.toUpperCase()}] ${s.action}`)
    console.log(`   Reason: ${s.reason}\n`)
  })
}

const cmd = process.argv[2]
if (cmd === 'status') status()
else if (cmd === 'analyze') analyze()
else if (cmd === 'improve') improve()
else {
  console.log('Usage: node scripts/agent.cjs <command>')
  console.log('Commands: status, analyze, improve')
  process.exit(1)
}
