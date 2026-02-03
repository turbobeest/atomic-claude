#!/usr/bin/env node
/**
 * ATOMIC CLAUDE - Tasks Dashboard Server
 * Lightweight Express server for real-time task monitoring
 */

const express = require('express');
const path = require('path');
const fs = require('fs');
const app = express();

const PORT = process.env.ATOMIC_TASKS_PORT || 5173;
const ATOMIC_ROOT = process.env.ATOMIC_ROOT || path.resolve(__dirname, '..');
const STATE_DIR = path.join(ATOMIC_ROOT, '.state');
const STATUS_FILE = path.join(STATE_DIR, 'current-task.json');
const TASK_STATE_FILE = path.join(ATOMIC_ROOT, '.claude', 'task-state.json');
const PROJECT_CONFIG = path.join(ATOMIC_ROOT, '.outputs', '0-setup', 'project-config.json');

// Ensure state directory exists
if (!fs.existsSync(STATE_DIR)) {
  fs.mkdirSync(STATE_DIR, { recursive: true });
}

// Middleware
app.use(express.static(path.join(__dirname, 'public')));
app.use(express.json());

// API: Get current task status
app.get('/api/status', (req, res) => {
  try {
    if (fs.existsSync(STATUS_FILE)) {
      const status = JSON.parse(fs.readFileSync(STATUS_FILE, 'utf8'));
      res.json(status);
    } else {
      res.json({
        active: false,
        message: 'No active task'
      });
    }
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

// API: Get task state (all completed/pending tasks)
app.get('/api/tasks', (req, res) => {
  try {
    if (fs.existsSync(TASK_STATE_FILE)) {
      const taskState = JSON.parse(fs.readFileSync(TASK_STATE_FILE, 'utf8'));
      res.json(taskState);
    } else {
      res.json({ phases: {} });
    }
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

// API: Get project configuration
app.get('/api/config', (req, res) => {
  try {
    if (fs.existsSync(PROJECT_CONFIG)) {
      const config = JSON.parse(fs.readFileSync(PROJECT_CONFIG, 'utf8'));
      res.json(config);
    } else {
      res.json({ project: { name: 'Not configured' } });
    }
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

// API: Server-Sent Events for real-time updates
app.get('/api/stream', (req, res) => {
  res.setHeader('Content-Type', 'text/event-stream');
  res.setHeader('Cache-Control', 'no-cache');
  res.setHeader('Connection', 'keep-alive');

  // Send initial status
  const sendStatus = () => {
    try {
      if (fs.existsSync(STATUS_FILE)) {
        const status = JSON.parse(fs.readFileSync(STATUS_FILE, 'utf8'));
        res.write(`data: ${JSON.stringify(status)}\n\n`);
      }
    } catch (error) {
      // Ignore errors during streaming
    }
  };

  sendStatus();

  // Watch for changes to status file
  let watcher = null;
  try {
    if (fs.existsSync(STATUS_FILE)) {
      watcher = fs.watch(STATUS_FILE, (eventType) => {
        if (eventType === 'change') {
          sendStatus();
        }
      });
    } else {
      // If file doesn't exist yet, poll for it
      const pollInterval = setInterval(() => {
        if (fs.existsSync(STATUS_FILE)) {
          clearInterval(pollInterval);
          watcher = fs.watch(STATUS_FILE, (eventType) => {
            if (eventType === 'change') {
              sendStatus();
            }
          });
        }
      }, 1000);

      req.on('close', () => {
        clearInterval(pollInterval);
      });
    }
  } catch (error) {
    // File watch failed, fall back to polling
    const pollInterval = setInterval(sendStatus, 2000);
    req.on('close', () => {
      clearInterval(pollInterval);
    });
  }

  // Clean up on client disconnect
  req.on('close', () => {
    if (watcher) {
      watcher.close();
    }
  });
});

// Serve index.html for all routes
app.get('*', (req, res) => {
  res.sendFile(path.join(__dirname, 'public', 'index.html'));
});

app.listen(PORT, () => {
  console.log(`\n  ✓ Tasks Dashboard: http://localhost:${PORT}`);
  console.log(`  State directory: ${STATE_DIR}\n`);
});
