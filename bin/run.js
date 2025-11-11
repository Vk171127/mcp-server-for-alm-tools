#!/usr/bin/env node

/**
 * Node.js wrapper for ALM Traceability MCP Server
 * This allows the Python MCP server to be run via npx
 */

const { spawn } = require('child_process');
const path = require('path');

// Get the directory where the package is installed
const packageDir = path.dirname(__dirname);

// Run the Python MCP server
const pythonProcess = spawn('python3', ['-m', 'mcp_main'], {
  cwd: packageDir,
  stdio: 'inherit',
  env: {
    ...process.env,
    PYTHONUNBUFFERED: '1'
  }
});

// Handle process termination
pythonProcess.on('error', (error) => {
  console.error('Failed to start MCP server:', error);
  process.exit(1);
});

pythonProcess.on('exit', (code) => {
  process.exit(code || 0);
});

// Handle Ctrl+C
process.on('SIGINT', () => {
  pythonProcess.kill('SIGINT');
});

process.on('SIGTERM', () => {
  pythonProcess.kill('SIGTERM');
});