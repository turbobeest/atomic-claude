#!/usr/bin/env node
/**
 * ATOMIC CLAUDE - Enhanced Tasks Dashboard Server
 * Includes memory flow tracking, task details, and phase management
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
const MEMORY_DIR = path.join(STATE_DIR, 'memory');

// Ensure directories exist
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

// API: Get task state with memory flow
app.get('/api/tasks', (req, res) => {
  try {
    if (fs.existsSync(TASK_STATE_FILE)) {
      const taskState = JSON.parse(fs.readFileSync(TASK_STATE_FILE, 'utf8'));

      // Enhance with memory flow data
      if (taskState.phases) {
        for (const [phaseId, phase] of Object.entries(taskState.phases)) {
          if (phase.tasks) {
            for (const [taskId, task] of Object.entries(phase.tasks)) {
              // Add memory flow metadata
              task.memory = getTaskMemoryFlow(phaseId, taskId);
            }
          }
        }
      }

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
      res.json({ project: { name: 'Unnamed Project' } });
    }
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

// API: Get task details (inputs/outputs)
app.get('/api/task/:phase/:taskId', (req, res) => {
  try {
    const { phase, taskId } = req.params;
    const phaseDir = path.join(ATOMIC_ROOT, '.outputs', phase);

    const details = {
      inputs: [],
      outputs: [],
      memory: getTaskMemoryFlow(phase, taskId)
    };

    // Scan for task-related files
    if (fs.existsSync(phaseDir)) {
      const files = fs.readdirSync(phaseDir);
      files.forEach(file => {
        const filePath = path.join(phaseDir, file);
        if (file.includes(taskId) || file.includes(phase)) {
          const stat = fs.statSync(filePath);
          const fileInfo = {
            name: file,
            path: filePath.replace(ATOMIC_ROOT, ''),
            size: stat.size,
            modified: stat.mtime
          };

          // Categorize as input or output based on naming
          if (file.includes('prompt') || file.includes('input') || file.includes('context')) {
            details.inputs.push(fileInfo);
          } else {
            details.outputs.push(fileInfo);
          }
        }
      });
    }

    res.json(details);
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

// API: Get memory stats
app.get('/api/memory/stats', (req, res) => {
  try {
    const stats = {
      recallDefinitions: 0,
      saveDefinitions: 0,
      debugEntries: 0,
      localFiles: 0
    };

    // Count task memory definitions
    const defsFile = path.join(ATOMIC_ROOT, 'lib', 'task-memory-defs.sh');
    if (fs.existsSync(defsFile)) {
      const content = fs.readFileSync(defsFile, 'utf8');
      stats.recallDefinitions = (content.match(/TASK_MEMORY_RECALL\[/g) || []).length;
      stats.saveDefinitions = (content.match(/TASK_MEMORY_SAVE\[/g) || []).length;
    }

    // Count memory debug entries
    const debugDir = path.join(STATE_DIR, 'memory-debug');
    if (fs.existsSync(debugDir)) {
      stats.debugEntries = fs.readdirSync(debugDir).length;
    }

    // Count local memory files
    if (fs.existsSync(MEMORY_DIR)) {
      const countFiles = (dir) => {
        let count = 0;
        const entries = fs.readdirSync(dir, { withFileTypes: true });
        for (const entry of entries) {
          if (entry.isDirectory()) {
            count += countFiles(path.join(dir, entry.name));
          } else {
            count++;
          }
        }
        return count;
      };
      stats.localFiles = countFiles(MEMORY_DIR);
    }

    res.json(stats);
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

// API: Server-Sent Events for real-time updates
app.get('/api/stream', (req, res) => {
  res.setHeader('Content-Type', 'text/event-stream');
  res.setHeader('Cache-Control', 'no-cache');
  res.setHeader('Connection', 'keep-alive');

  const sendStatus = () => {
    try {
      if (fs.existsSync(STATUS_FILE)) {
        const status = JSON.parse(fs.readFileSync(STATUS_FILE, 'utf8'));
        res.write(`data: ${JSON.stringify(status)}\n\n`);
      }
    } catch (error) {
      // Ignore streaming errors
    }
  };

  sendStatus();

  let watcher = null;
  try {
    if (fs.existsSync(STATUS_FILE)) {
      watcher = fs.watch(STATUS_FILE, (eventType) => {
        if (eventType === 'change') {
          sendStatus();
        }
      });
    } else {
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
    const pollInterval = setInterval(sendStatus, 2000);
    req.on('close', () => {
      clearInterval(pollInterval);
    });
  }

  req.on('close', () => {
    if (watcher) {
      watcher.close();
    }
  });
});

// Helper: Get memory flow for a task
function getTaskMemoryFlow(phaseId, taskId) {
  const memoryFlow = {
    recalled: false,
    saved: false,
    pendingRecall: false,
    pendingSave: false,
    inProgress: false,
    failed: false,
    injected: false,
    written: false,
    local: false,
    remote: false
  };

  // Check memory debug logs
  const debugDir = path.join(STATE_DIR, 'memory-debug');
  if (fs.existsSync(debugDir)) {
    const debugFiles = fs.readdirSync(debugDir);
    debugFiles.forEach(file => {
      if (file.includes(phaseId) && file.includes(taskId)) {
        try {
          const content = fs.readFileSync(path.join(debugDir, file), 'utf8');
          if (content.includes('recall_success')) memoryFlow.recalled = true;
          if (content.includes('save_success')) memoryFlow.saved = true;
          if (content.includes('recall_start')) memoryFlow.pendingRecall = true;
          if (content.includes('save_start')) memoryFlow.pendingSave = true;
          if (content.includes('in_progress')) memoryFlow.inProgress = true;
          if (content.includes('error') || content.includes('fail')) memoryFlow.failed = true;
        } catch (err) {
          // Ignore read errors
        }
      }
    });
  }

  // Check local memory files
  const taskMemoryDir = path.join(MEMORY_DIR, `phase-${phaseId}`);
  if (fs.existsSync(taskMemoryDir)) {
    const files = fs.readdirSync(taskMemoryDir);
    if (files.some(f => f.includes(taskId))) {
      memoryFlow.local = true;
    }
  }

  return memoryFlow;
}

// Serve index.html for all other routes
app.get('*', (req, res) => {
  res.sendFile(path.join(__dirname, 'public', 'index-enhanced.html'));
});

app.listen(PORT, () => {
  console.log(`\n  ✓ Enhanced Tasks Dashboard: http://localhost:${PORT}`);
  console.log(`  Root: ${ATOMIC_ROOT}`);
  console.log(`  State: ${STATE_DIR}\n`);
});
