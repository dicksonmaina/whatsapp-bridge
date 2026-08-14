@echo off
echo Starting MCP Filesystem Server...
echo Allowed roots:
echo   - C:\Users\user\whatsapp-bridge
echo   - C:\Users\user\.openclaw
echo   - C:\Users\user\.hermes
echo   - C:\Users\user\Desktop\javascript
echo.

cd /d "C:\Users\user\whatsapp-bridge"

REM Start MCP filesystem server with stdio transport
REM The server communicates via stdin/stdout using MCP protocol
REM Logs are written to stderr
npx mcp-server-filesystem ^
  "C:\Users\user\whatsapp-bridge" ^
  "C:\Users\user\.openclaw" ^
  "C:\Users\user\.hermes" ^
  "C:\Users\user\Desktop\javascript"
