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
app.use(express.static(path.join(__dirname, 'public'), {
  setHeaders: (res, path) => {
    // Disable caching for HTML to ensure updates are always fresh
    if (path.endsWith('.html')) {
      res.setHeader('Cache-Control', 'no-cache, no-store, must-revalidate');
      res.setHeader('Pragma', 'no-cache');
      res.setHeader('Expires', '0');
    }
  }
}));
app.use(express.json());

// API: Get current task status with staleness detection
app.get('/api/status', (req, res) => {
  try {
    if (fs.existsSync(STATUS_FILE)) {
      const status = JSON.parse(fs.readFileSync(STATUS_FILE, 'utf8'));

      // Check staleness against the most recent of current-task.json OR task-state.json
      // (current-task.json tracks LLM invocations, task-state.json tracks task completions)
      let mostRecentTime = fs.statSync(STATUS_FILE).mtimeMs;

      if (fs.existsSync(TASK_STATE_FILE)) {
        const taskStateTime = fs.statSync(TASK_STATE_FILE).mtimeMs;
        mostRecentTime = Math.max(mostRecentTime, taskStateTime);
      }

      const ageSeconds = Math.floor((Date.now() - mostRecentTime) / 1000);

      // Add staleness metadata
      status.file_age_seconds = ageSeconds;
      status.is_stale = ageSeconds > 60; // No update in 60+ seconds
      status.last_modified = new Date(mostRecentTime).toISOString();

      res.json(status);
    } else {
      res.json({
        active: false,
        message: 'No active task',
        is_stale: true
      });
    }
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

// API: Get task state with memory flow and file artifacts
app.get('/api/tasks', (req, res) => {
  try {
    if (fs.existsSync(TASK_STATE_FILE)) {
      const taskState = JSON.parse(fs.readFileSync(TASK_STATE_FILE, 'utf8'));

      // Enhance with memory flow data and file artifacts
      if (taskState.phases) {
        for (const [phaseId, phase] of Object.entries(taskState.phases)) {
          if (phase.tasks) {
            for (const [taskId, task] of Object.entries(phase.tasks)) {
              // Add memory flow metadata
              task.memory = getTaskMemoryFlow(phaseId, taskId);

              // Add file artifacts
              task.files = getTaskFiles(phaseId, taskId);
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
    let config = { project: { name: 'Unnamed Project' } };

    if (fs.existsSync(PROJECT_CONFIG)) {
      config = JSON.parse(fs.readFileSync(PROJECT_CONFIG, 'utf8'));
    }

    // Extract project name with intelligent fallbacks
    let projectName = config.extracted?.project?.name || config.project?.name;

    // If project name is a test value or missing, read directly from setup.md
    if (!projectName || projectName === 'atomic-test' || projectName === 'test-project') {
      const setupFile = path.join(ATOMIC_ROOT, 'initialization', 'setup.md');
      if (fs.existsSync(setupFile)) {
        const setupContent = fs.readFileSync(setupFile, 'utf8');

        // First priority: Look for **name** field
        const nameMatch = setupContent.match(/^\*\*name\*\*:\s*(.+)$/m);
        if (nameMatch && nameMatch[1].trim() &&
            nameMatch[1].trim() !== 'atomic-test' &&
            nameMatch[1].trim() !== 'test-project') {
          projectName = nameMatch[1].trim();
        } else {
          // Second priority: Look for first heading (e.g., "# WeatherWise")
          const headingMatch = setupContent.match(/^#\s+([^\n]+)/m);
          if (headingMatch) {
            const heading = headingMatch[1].replace(/\s+Configuration$/i, '').trim();
            if (heading.toLowerCase() !== 'test project' &&
                heading.toLowerCase() !== 'atomic claude') {
              projectName = heading;
            }
          }
        }
      }

      // Ultimate fallback: use repo directory name, prettified
      if (!projectName || projectName === 'atomic-test' || projectName === 'test-project') {
        const repoName = path.basename(ATOMIC_ROOT);
        projectName = repoName
          .split('-')
          .map(w => w.charAt(0).toUpperCase() + w.slice(1))
          .join(' ');
      }
    }

    // Update config with resolved name
    if (!config.project) config.project = {};
    config.project.name = projectName;

    res.json(config);
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

        // Add staleness detection (same as /api/status)
        let mostRecentTime = fs.statSync(STATUS_FILE).mtimeMs;
        if (fs.existsSync(TASK_STATE_FILE)) {
          const taskStateTime = fs.statSync(TASK_STATE_FILE).mtimeMs;
          mostRecentTime = Math.max(mostRecentTime, taskStateTime);
        }
        const ageSeconds = Math.floor((Date.now() - mostRecentTime) / 1000);

        status.file_age_seconds = ageSeconds;
        status.is_stale = ageSeconds > 60; // No update in 60+ seconds
        status.last_modified = new Date(mostRecentTime).toISOString();

        res.write(`data: ${JSON.stringify(status)}\n\n`);
      } else {
        // Send explicit inactive status when file doesn't exist
        res.write(`data: ${JSON.stringify({
          active: false,
          message: 'No active task',
          provider: null,
          model: null,
          is_stale: false
        })}\n\n`);
      }
    } catch (error) {
      // Send error status on exception
      res.write(`data: ${JSON.stringify({
        active: false,
        error: true,
        message: 'Error reading status',
        is_stale: true
      })}\n\n`);
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
  // Extract phase number from phaseId (e.g., "0-setup" -> "0")
  const phaseNum = phaseId.split('-')[0];
  const taskMemoryDir = path.join(MEMORY_DIR, `phase-${phaseNum}`);
  if (fs.existsSync(taskMemoryDir)) {
    const files = fs.readdirSync(taskMemoryDir);

    // Check if task has a specific memory file
    if (files.some(f => f.includes(taskId))) {
      memoryFlow.local = true;
    }

    // Special case: final tasks (009, 110, 209, etc.) save to closeout.md
    // Check if this is a closeout task and closeout.md exists
    if (taskId.endsWith('09') || taskId.endsWith('10')) {
      if (files.includes('closeout.md')) {
        memoryFlow.local = true;
      }
    }
  }

  return memoryFlow;
}

// Helper: Get file artifacts for a task
function getTaskFiles(phaseId, taskId) {
  const files = { read: [], written: [] };
  const phaseDir = path.join(ATOMIC_ROOT, '.outputs', phaseId);

  if (!fs.existsSync(phaseDir)) {
    return files;
  }

  // Known input patterns (files read by task)
  const inputPatterns = [
    'prompt', 'input', 'context', 'material', 'corpus',
    'requirements', 'reference', 'setup', 'config'
  ];

  // Known output patterns (files written by task)
  const outputPatterns = [
    'response', 'output', 'result', 'extracted', 'generated',
    'summary', 'decisions', 'artifacts', 'session', 'metadata',
    'current-task', 'selected', 'approved', 'validated', 'secrets'
  ];

  // Recursively scan directory and subdirectories
  const scanDirectory = (dirPath, relativePath = '') => {
    try {
      const entries = fs.readdirSync(dirPath, { withFileTypes: true });

      entries.forEach(entry => {
        const fullPath = path.join(dirPath, entry.name);
        const relPath = relativePath ? path.join(relativePath, entry.name) : entry.name;

        if (entry.isDirectory()) {
          // Recursively scan subdirectories
          scanDirectory(fullPath, relPath);
        } else {
          try {
            const stat = fs.statSync(fullPath);
            const fileInfo = {
              name: relPath,
              path: fullPath.replace(ATOMIC_ROOT, ''),
              size: stat.size,
              modified: stat.mtime
            };

            // Check if file is related to this task
            // Be more inclusive: match task ID, or show all files for certain phases
            const isRelated = relPath.includes(taskId) ||
                             relPath.includes(phaseId) ||
                             phaseId === '0-setup' ||  // Show all files for phase 0
                             phaseId === '1-discovery' ||  // Show all files for phase 1
                             phaseId === '2-prd' ||  // Show all files for phase 2
                             relPath === 'session.json' ||
                             relPath === 'metadata.json' ||
                             relPath === 'current-task.json' ||
                             relPath === 'closeout.md' ||
                             relPath === 'closeout.json';

            if (!isRelated) return;

            // Categorize as input (read) or output (written)
            const lowerName = relPath.toLowerCase();
            const isInput = inputPatterns.some(p => lowerName.includes(p)) ||
                           (relPath.endsWith('.md') && !lowerName.includes('output'));

            const isOutput = outputPatterns.some(p => lowerName.includes(p)) ||
                            relPath.endsWith('.json') ||
                            relPath.endsWith('.err');

            if (isInput && !isOutput) {
              files.read.push(fileInfo);
            } else {
              files.written.push(fileInfo);
            }
          } catch (err) {
            // Skip files we can't stat
          }
        }
      });
    } catch (error) {
      // Directory read failed, skip
    }
  };

  scanDirectory(phaseDir);

  // Sort by name
  files.read.sort((a, b) => a.name.localeCompare(b.name));
  files.written.sort((a, b) => a.name.localeCompare(b.name));

  return files;
}

// API: Get file content for viewing
app.get('/api/file', (req, res) => {
  try {
    const filePath = req.query.path;
    if (!filePath) {
      return res.status(400).json({ error: 'Missing path parameter' });
    }

    // Security: ensure path is within ATOMIC_ROOT
    const fullPath = path.join(ATOMIC_ROOT, filePath);
    if (!fullPath.startsWith(ATOMIC_ROOT)) {
      return res.status(403).json({ error: 'Access denied' });
    }

    if (!fs.existsSync(fullPath)) {
      return res.status(404).json({ error: 'File not found' });
    }

    const stat = fs.statSync(fullPath);
    if (stat.isDirectory()) {
      return res.status(400).json({ error: 'Path is a directory' });
    }

    // Read file with size limit (1MB)
    if (stat.size > 1024 * 1024) {
      return res.json({
        content: '[File too large to display (>1MB)]',
        truncated: true,
        size: stat.size
      });
    }

    const content = fs.readFileSync(fullPath, 'utf8');
    res.json({
      content,
      size: stat.size,
      modified: stat.mtime
    });
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

// Serve index.html for all other routes
app.get('*', (req, res) => {
  res.sendFile(path.join(__dirname, 'public', 'index.html'));
});

app.listen(PORT, () => {
  console.log(`\n  ✓ Enhanced Tasks Dashboard: http://localhost:${PORT}`);
  console.log(`  Root: ${ATOMIC_ROOT}`);
  console.log(`  State: ${STATE_DIR}\n`);
});
