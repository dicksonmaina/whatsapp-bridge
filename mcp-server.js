const { execFile } = require('child_process');
const path = require('path');

const CONFIG_PATH = path.join(__dirname, 'mcp-config.json');
const config = JSON.parse(require('fs').readFileSync(CONFIG_PATH, 'utf-8'));

const server = execFile(
  'npx',
  ['mcp-server-filesystem', ...config.roots],
  { cwd: __dirname }
);

server.stdout.on('data', (data) => {
  process.stdout.write(`[mcp-stdout] ${data}`);
});

server.stderr.on('data', (data) => {
  process.stderr.write(`[mcp-stderr] ${data}`);
});

server.on('exit', (code) => {
  console.log(`MCP filesystem server exited with code ${code}`);
});

process.on('SIGINT', () => {
  server.kill('SIGINT');
  process.exit(0);
});
