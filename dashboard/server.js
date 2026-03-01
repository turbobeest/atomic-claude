#!/usr/bin/env node
/**
 * ATOMIC CLAUDE - Enhanced Tasks Dashboard Server
 * Includes memory flow tracking, task details, and phase management
 */

const express = require('express');
const path = require('path');
const fs = require('fs');
const { createClient } = require('redis');
const app = express();

const PORT = process.env.ATOMIC_TASKS_PORT || 5174;
const ATOMIC_ROOT = process.env.ATOMIC_ROOT || path.resolve(__dirname, '..');

// When atomic-claude is deployed in a host project, both .state/ and .outputs/
// live in the PROJECT ROOT (host), not inside atomic-claude/ itself.
// Auto-detect: if .state/ or .outputs/ exist in parent, use parent as PROJECT_ROOT.
const PROJECT_ROOT = fs.existsSync(path.join(ATOMIC_ROOT, '.state'))
  ? ATOMIC_ROOT
  : fs.existsSync(path.join(path.resolve(ATOMIC_ROOT, '..'), '.state'))
    ? path.resolve(ATOMIC_ROOT, '..')
    : fs.existsSync(path.join(path.resolve(ATOMIC_ROOT, '..'), '.outputs'))
      ? path.resolve(ATOMIC_ROOT, '..')
      : ATOMIC_ROOT;

const STATE_DIR = path.join(PROJECT_ROOT, '.state');
const STATUS_FILE = path.join(STATE_DIR, 'current-task.json');
const TASK_STATE_FILE = path.join(STATE_DIR, 'task-state.json');
const MEMORY_DIR = path.join(STATE_DIR, 'memory');
const OUTPUTS_DIR = path.join(PROJECT_ROOT, '.outputs');
const PROJECT_CONFIG = path.join(OUTPUTS_DIR, '0-setup', 'project-config.json');

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

// API: Report this server's ATOMIC_ROOT (used by start-dashboard.sh to detect stale instances)
app.get('/api/root', (req, res) => {
  res.json({ root: ATOMIC_ROOT });
});

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
      status.is_stale = ageSeconds > 300; // No update in 5+ minutes (interactive prompts can take time)
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

              // Add file artifacts (use task's own artifacts list)
              task.files = getTaskFiles(phaseId, taskId, task.artifacts || []);
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
    let config = { project: { name: null } };

    if (fs.existsSync(PROJECT_CONFIG)) {
      config = JSON.parse(fs.readFileSync(PROJECT_CONFIG, 'utf8'));
    }

    // Extract project name with intelligent fallbacks
    let projectName = config.extracted?.project?.name || config.project?.name;

    // If project name is a test value or missing, read directly from setup files
    if (!projectName || projectName === 'atomic-test' || projectName === 'test-project') {
      // Check both setup.md (user project file) and SETUP-GUIDE.md (template)
      const setupFile = path.join(ATOMIC_ROOT, 'initialization', 'setup.md');
      const setupGuideFile = path.join(ATOMIC_ROOT, 'initialization', 'SETUP-GUIDE.md');
      const filesToCheck = [setupFile, setupGuideFile].filter(f => fs.existsSync(f));

      for (const f of filesToCheck) {
        const setupContent = fs.readFileSync(f, 'utf8');

        // Look for **name** field (works in both setup.md and SETUP-GUIDE.md)
        const nameMatch = setupContent.match(/^\*\*name\*\*:\s*(.+)$/m);
        if (nameMatch && nameMatch[1].trim() &&
            nameMatch[1].trim() !== 'atomic-test' &&
            nameMatch[1].trim() !== 'test-project') {
          projectName = nameMatch[1].trim();
          break;
        }

        // Heading fallback only for setup.md (user's project file), not the template
        if (f === setupFile) {
          const headingMatch = setupContent.match(/^#\s+([^\n]+)/m);
          if (headingMatch) {
            const heading = headingMatch[1].replace(/\s+Configuration$/i, '').trim();
            if (heading.toLowerCase() !== 'test project' &&
                heading.toLowerCase() !== 'atomic claude' &&
                heading.toLowerCase() !== 'setup guide') {
              projectName = heading;
              break;
            }
          }
        }
      }

      // Ultimate fallback: use project directory name, prettified
      // Detect host project: if ATOMIC_ROOT basename is "atomic-claude" and a
      // parent directory exists with .outputs/ or its own project files, use the
      // parent name instead (e.g., "eloreum" instead of "atomic-claude")
      if (!projectName || projectName === 'atomic-test' || projectName === 'test-project') {
        let nameSource = ATOMIC_ROOT;
        const atomicBasename = path.basename(ATOMIC_ROOT).toLowerCase();
        if (atomicBasename === 'atomic-claude' || atomicBasename === 'atomic-claude2') {
          const parentDir = path.resolve(ATOMIC_ROOT, '..');
          // If parent has .outputs/ or other project indicators, it's a host project
          if (fs.existsSync(path.join(parentDir, '.outputs')) ||
              fs.existsSync(path.join(parentDir, 'src')) ||
              fs.existsSync(path.join(parentDir, 'package.json'))) {
            nameSource = parentDir;
          }
        }
        const repoName = path.basename(nameSource);
        projectName = repoName
          .split(/[-_]/)
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
    const phaseDir = path.join(OUTPUTS_DIR, phase);

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
      phasesTracked: 0,
      taskFiles: 0,
      avgEntrySize: 0,
      debugEntries: 0
    };

    // Count phases and task memory files
    if (fs.existsSync(MEMORY_DIR)) {
      const phaseDirs = fs.readdirSync(MEMORY_DIR, { withFileTypes: true })
        .filter(e => e.isDirectory() && e.name.startsWith('phase-'));
      stats.phasesTracked = phaseDirs.length;

      let totalSize = 0;
      let fileCount = 0;
      for (const phaseDir of phaseDirs) {
        const phasePath = path.join(MEMORY_DIR, phaseDir.name);
        const files = fs.readdirSync(phasePath).filter(f => f.endsWith('.md'));
        for (const file of files) {
          const content = fs.readFileSync(path.join(phasePath, file), 'utf8');
          totalSize += content.length;
          fileCount++;
        }
      }
      stats.taskFiles = fileCount;
      stats.avgEntrySize = fileCount > 0 ? Math.round(totalSize / fileCount) : 0;
    }

    // Count memory debug entries
    const debugDir = path.join(STATE_DIR, 'memory-debug');
    if (fs.existsSync(debugDir)) {
      stats.debugEntries = fs.readdirSync(debugDir).length;
    }

    res.json(stats);
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

// API: Memory entries — read actual memory files from .state/memory/
// Also enriches with structured metadata from memory.json when available
app.get('/api/memory/entries', (req, res) => {
  try {
    const entries = [];

    // Load metadata index from memory.json for enrichment
    const metadataIndex = {};
    const memoryJsonFile = path.join(STATE_DIR, 'memory.json');
    if (fs.existsSync(memoryJsonFile)) {
      try {
        const memoryData = JSON.parse(fs.readFileSync(memoryJsonFile, 'utf8'));
        for (const entry of (memoryData.entries || [])) {
          if (entry.task_id) {
            metadataIndex[entry.task_id] = entry.metadata || {};
          }
        }
      } catch (err) {
        // Ignore parse errors
      }
    }

    if (fs.existsSync(MEMORY_DIR)) {
      // Walk phase directories
      const phaseDirs = fs.readdirSync(MEMORY_DIR, { withFileTypes: true })
        .filter(d => d.isDirectory() && d.name.startsWith('phase-'))
        .sort((a, b) => a.name.localeCompare(b.name));

      for (const phaseDir of phaseDirs) {
        const phasePath = path.join(MEMORY_DIR, phaseDir.name);
        const files = fs.readdirSync(phasePath)
          .filter(f => f.endsWith('.md'))
          .sort();

        for (const file of files) {
          const filePath = path.join(phasePath, file);
          const content = fs.readFileSync(filePath, 'utf8');
          const stat = fs.statSync(filePath);

          // Extract task_id from filename (e.g., "task_002.md" -> "002")
          const taskIdMatch = file.match(/task_(\d+)/);
          const taskId = taskIdMatch ? taskIdMatch[1] : null;

          // Parse the markdown memory format:
          // ## type - timestamp\n\nContent\n\nTags: ...\n\n---
          const sections = content.split('---').filter(s => s.trim());
          for (const section of sections) {
            const headerMatch = section.match(/##\s+(\S+)\s+-\s+(.+)/);
            const tagsMatch = section.match(/Tags:\s+(.+)/);
            // Content is everything between header line and Tags line
            const lines = section.trim().split('\n');
            const contentLines = [];
            let pastHeader = false;
            for (const line of lines) {
              if (line.startsWith('## ')) { pastHeader = true; continue; }
              if (line.startsWith('Tags:')) continue;
              if (pastHeader && line.trim()) contentLines.push(line.trim());
            }

            const entry = {
              phase: phaseDir.name,
              file: file,
              type: headerMatch ? headerMatch[1] : 'unknown',
              timestamp: headerMatch ? headerMatch[2].trim() : stat.mtime.toISOString(),
              content: contentLines.join('\n'),
              tags: tagsMatch ? tagsMatch[1].split(',').map(t => t.trim()) : [],
            };

            // Enrich with structured metadata from memory.json
            if (taskId && metadataIndex[taskId]) {
              entry.metadata = metadataIndex[taskId];
            }

            // Include source file path for detail view
            entry.filePath = path.relative(ATOMIC_ROOT, filePath);
            entry.taskId = taskId;

            entries.push(entry);
          }
        }
      }
    }

    // Sort by timestamp descending (newest first)
    entries.sort((a, b) => b.timestamp.localeCompare(a.timestamp));
    res.json({ entries, total: entries.length });
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

// API: Memory detail — returns full memory content + associated output artifacts
app.get('/api/memory/detail', (req, res) => {
  try {
    const { phase, taskId } = req.query;
    if (!phase || !taskId) {
      return res.status(400).json({ error: 'Missing phase or taskId parameter' });
    }

    const result = {
      memoryContent: null,
      taskInfo: null,
      artifacts: [],
      outputFiles: []
    };

    // 1. Read the raw memory markdown file
    const memoryFile = path.join(MEMORY_DIR, phase, `task_${taskId}.md`);
    if (fs.existsSync(memoryFile)) {
      result.memoryContent = fs.readFileSync(memoryFile, 'utf8');
    }

    // 2. Get task info from task-state.json (status, timestamps, artifacts)
    if (fs.existsSync(TASK_STATE_FILE)) {
      try {
        const taskState = JSON.parse(fs.readFileSync(TASK_STATE_FILE, 'utf8'));
        const phases = taskState.phases || {};
        // Find the task across phases by task ID
        for (const [phaseId, phaseData] of Object.entries(phases)) {
          const tasks = phaseData.tasks || {};
          if (tasks[taskId]) {
            result.taskInfo = {
              ...tasks[taskId],
              phaseId: phaseId
            };
            break;
          }
        }
      } catch (err) {
        // Ignore parse errors
      }
    }

    // 3. Load associated artifact contents (preview: first 3KB each)
    if (result.taskInfo && result.taskInfo.artifacts) {
      for (const artifactPath of result.taskInfo.artifacts) {
        try {
          // Resolve path — multiple strategies to handle symlinks and path mismatches
          let fullPath = path.isAbsolute(artifactPath)
            ? artifactPath
            : path.join(ATOMIC_ROOT, artifactPath);

          if (!fs.existsSync(fullPath)) {
            // Strategy 1: Extract .outputs/ relative path and try under PROJECT_ROOT
            const outputsIdx = artifactPath.indexOf('.outputs/');
            if (outputsIdx >= 0) {
              const relFromOutputs = artifactPath.slice(outputsIdx);
              const projPath = path.join(path.resolve(PROJECT_ROOT), relFromOutputs);
              if (fs.existsSync(projPath)) {
                fullPath = projPath;
              }
            }
          }

          if (!fs.existsSync(fullPath)) {
            // Strategy 2: Resolve symlinks in ATOMIC_ROOT and try matching
            try {
              const realAtomic = fs.realpathSync(ATOMIC_ROOT);
              const realProject = fs.realpathSync(PROJECT_ROOT);
              // Replace realpath-based atomic root in the stored path
              if (artifactPath.includes(realAtomic)) {
                const altPath = artifactPath.replace(realAtomic, realProject);
                if (fs.existsSync(altPath)) fullPath = altPath;
              }
            } catch (e) { /* ignore */ }
          }

          if (!fs.existsSync(fullPath)) continue;

          const stat = fs.statSync(fullPath);
          // Skip secrets
          if (path.basename(fullPath) === 'secrets.json') continue;

          let preview = '';
          if (stat.size <= 3072) {
            preview = fs.readFileSync(fullPath, 'utf8');
          } else {
            const buf = Buffer.alloc(3072);
            const fd = fs.openSync(fullPath, 'r');
            fs.readSync(fd, buf, 0, 3072, 0);
            fs.closeSync(fd);
            preview = buf.toString('utf8') + '\n... (truncated)';
          }

          result.artifacts.push({
            name: path.basename(fullPath),
            path: artifactPath,
            size: stat.size,
            modified: stat.mtime,
            preview: preview
          });
        } catch (err) {
          // Skip unreadable artifacts
        }
      }
    }

    // 4. List all files in the phase output directory (for discovery)
    if (result.taskInfo && result.taskInfo.phaseId) {
      const phaseOutputDir = path.join(OUTPUTS_DIR, result.taskInfo.phaseId);
      if (fs.existsSync(phaseOutputDir)) {
        try {
          const walkDir = (dir, prefix = '') => {
            const items = fs.readdirSync(dir, { withFileTypes: true });
            for (const item of items) {
              const relPath = prefix ? `${prefix}/${item.name}` : item.name;
              if (item.isDirectory()) {
                // Skip deeply nested dirs (prompts/, etc.) — just list top-level
                if (!prefix) walkDir(path.join(dir, item.name), relPath);
              } else {
                const stat = fs.statSync(path.join(dir, item.name));
                result.outputFiles.push({
                  name: relPath,
                  size: stat.size,
                  modified: stat.mtime
                });
              }
            }
          };
          walkDir(phaseOutputDir);
        } catch (err) {
          // Ignore walk errors
        }
      }
    }

    res.json(result);
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
        status.is_stale = ageSeconds > 300; // No update in 5+ minutes (interactive prompts can take time)
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

// API: Memory SSE stream — real-time memory entry feed
const MEMORY_JSON_FILE = path.join(STATE_DIR, 'memory.json');

app.get('/api/memory/stream', (req, res) => {
  res.setHeader('Content-Type', 'text/event-stream');
  res.setHeader('Cache-Control', 'no-cache');
  res.setHeader('Connection', 'keep-alive');

  let lastKnownCount = 0;
  let watcher = null;
  let pollInterval = null;
  let debounceTimer = null;

  // Read memory.json and return entries array
  const readEntries = () => {
    try {
      if (!fs.existsSync(MEMORY_JSON_FILE)) return [];
      const data = JSON.parse(fs.readFileSync(MEMORY_JSON_FILE, 'utf8'));
      return data.entries || [];
    } catch (err) {
      return [];
    }
  };

  // Derive categories from entry metadata (matches TaskMemory categories)
  const deriveCategories = (entry) => {
    const cats = [];
    const meta = entry.metadata || {};
    if (meta.warnings && meta.warnings.length) cats.push('warning');
    if (meta.decisions && meta.decisions.length) cats.push('decision');
    if (meta.findings && meta.findings.length) cats.push('finding');
    if (meta.configurations && meta.configurations.length) cats.push('configuration');
    if (meta.conversations && meta.conversations.length) cats.push('conversation');
    if (cats.length === 0) {
      // Fall back to entry_type
      const et = entry.entry_type || '';
      if (et === 'phase_closeout' || et === 'checkpoint' || et === 'task_start') {
        cats.push('system');
      } else {
        cats.push('finding');
      }
    }
    return cats;
  };

  // Enrich entry with categories
  const enrichEntry = (entry) => ({
    ...entry,
    categories: deriveCategories(entry),
  });

  // Send initial backfill
  const entries = readEntries();
  lastKnownCount = entries.length;
  const enriched = entries.map(enrichEntry);
  res.write(`event: init\ndata: ${JSON.stringify({ entries: enriched, total: enriched.length })}\n\n`);

  // Check for new entries (debounced)
  const checkForNew = () => {
    if (debounceTimer) clearTimeout(debounceTimer);
    debounceTimer = setTimeout(() => {
      try {
        const current = readEntries();
        if (current.length > lastKnownCount) {
          // Send only new entries
          const newEntries = current.slice(lastKnownCount);
          for (const entry of newEntries) {
            res.write(`event: entry\ndata: ${JSON.stringify(enrichEntry(entry))}\n\n`);
          }
          lastKnownCount = current.length;
        }
      } catch (err) {
        // Ignore read errors
      }
    }, 100); // 100ms debounce for rapid writes
  };

  // Watch memory.json for changes
  const startWatching = () => {
    try {
      if (fs.existsSync(MEMORY_JSON_FILE)) {
        watcher = fs.watch(MEMORY_JSON_FILE, (eventType) => {
          if (eventType === 'change' || eventType === 'rename') {
            checkForNew();
          }
        });
        // Also watch the directory in case file is recreated (atomic write)
        return true;
      }
      return false;
    } catch (err) {
      return false;
    }
  };

  if (!startWatching()) {
    // File doesn't exist yet — poll until it appears
    pollInterval = setInterval(() => {
      if (startWatching()) {
        clearInterval(pollInterval);
        pollInterval = null;
        // Check for entries that appeared while we waited
        checkForNew();
      }
    }, 2000);
  }

  // Cleanup on disconnect
  req.on('close', () => {
    if (watcher) watcher.close();
    if (pollInterval) clearInterval(pollInterval);
    if (debounceTimer) clearTimeout(debounceTimer);
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
// Uses the task's own artifacts list from task-state.json for precise per-task files.
function getTaskFiles(phaseId, taskId, artifacts) {
  const files = { read: [], written: [] };

  if (!artifacts || artifacts.length === 0) {
    return files;
  }

  for (const artifactPath of artifacts) {
    try {
      // Resolve to absolute path (artifacts may be absolute or relative)
      const fullPath = path.isAbsolute(artifactPath)
        ? artifactPath
        : path.join(ATOMIC_ROOT, artifactPath);

      if (!fs.existsSync(fullPath)) continue;

      const stat = fs.statSync(fullPath);
      // Derive display name: relative to phase output dir, or just the filename
      const phaseOutputDir = path.join(OUTPUTS_DIR, phaseId);
      let displayName;
      if (fullPath.startsWith(phaseOutputDir)) {
        displayName = path.relative(phaseOutputDir, fullPath);
      } else {
        displayName = path.basename(fullPath);
      }
      // Build a serveable path: relative to ATOMIC_ROOT or PROJECT_ROOT
      let servePath;
      if (fullPath.startsWith(ATOMIC_ROOT)) {
        servePath = fullPath.replace(ATOMIC_ROOT, '');
      } else if (PROJECT_ROOT !== ATOMIC_ROOT && fullPath.startsWith(PROJECT_ROOT)) {
        servePath = fullPath.replace(PROJECT_ROOT, '');
      } else {
        servePath = fullPath;  // absolute fallback
      }
      const fileInfo = {
        name: displayName,
        path: servePath,
        size: stat.size,
        modified: stat.mtime
      };

      files.written.push(fileInfo);
    } catch (err) {
      // Skip files we can't stat
    }
  }

  // Sort by name
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

    // Resolve full path — try relative to ATOMIC_ROOT first, then PROJECT_ROOT
    let fullPath;
    if (path.isAbsolute(filePath)) {
      fullPath = filePath;
    } else {
      fullPath = path.join(ATOMIC_ROOT, filePath);
      if (!fs.existsSync(fullPath) && PROJECT_ROOT !== ATOMIC_ROOT) {
        const altPath = path.join(PROJECT_ROOT, filePath);
        if (fs.existsSync(altPath)) {
          fullPath = altPath;
        }
      }
    }

    // Security: ensure path is within ATOMIC_ROOT or PROJECT_ROOT
    const resolvedPath = path.resolve(fullPath);
    const resolvedAtomic = path.resolve(ATOMIC_ROOT);
    const resolvedProject = path.resolve(PROJECT_ROOT);
    if (!resolvedPath.startsWith(resolvedAtomic) && !resolvedPath.startsWith(resolvedProject)) {
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

// ============================================================================
// NEW FEATURES - 2026-02-10
// ============================================================================

// API: Get token usage and cost tracking
app.get('/api/tokens', (req, res) => {
  try {
    const tokenFile = path.join(STATE_DIR, 'session-tokens.json');
    if (fs.existsSync(tokenFile)) {
      const data = JSON.parse(fs.readFileSync(tokenFile, 'utf8'));
      res.json(data);
    } else {
      res.json({
        total_input_tokens: 0,
        total_output_tokens: 0,
        estimated_cost_usd: 0,
        by_provider: {},
        by_model: {}
      });
    }
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

// API: Get error log
app.get('/api/errors', (req, res) => {
  try {
    const errorLog = path.join(ATOMIC_ROOT, '.logs', 'errors.json');
    if (fs.existsSync(errorLog)) {
      const errors = JSON.parse(fs.readFileSync(errorLog, 'utf8'));
      res.json(errors);
    } else {
      res.json({ errors: [] });
    }
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

// API: Get agent assignments
app.get('/api/agents', (req, res) => {
  try {
    const agentFiles = [
      path.join(OUTPUTS_DIR, '1-discovery', 'selected-agents.json'),
      path.join(OUTPUTS_DIR, '3-tasking', 'selected-agents.json')
    ];

    const agents = [];
    agentFiles.forEach(file => {
      if (fs.existsSync(file)) {
        const data = JSON.parse(fs.readFileSync(file, 'utf8'));
        if (data.discovery_agents) agents.push(...data.discovery_agents);
        if (data.decomposition_agents) agents.push(...data.decomposition_agents);
      }
    });

    res.json({ agents: [...new Set(agents)] });
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

// API: Get timeline data
app.get('/api/timeline', (req, res) => {
  try {
    const timeline = [];
    const taskStateFile = path.join(STATE_DIR, 'task-state.json');

    if (fs.existsSync(taskStateFile)) {
      const state = JSON.parse(fs.readFileSync(taskStateFile, 'utf8'));

      for (const [phaseId, phase] of Object.entries(state.phases || {})) {
        for (const [taskId, task] of Object.entries(phase.tasks || {})) {
          if (task.completed_at) {
            const startTime = task.started_at || task.completed_at;
            const endTime = task.completed_at;
            const duration = new Date(endTime) - new Date(startTime);

            timeline.push({
              phase: phaseId,
              task: taskId,
              name: task.name || `Task ${taskId}`,
              start: startTime,
              end: endTime,
              duration_ms: duration,
              duration_seconds: Math.floor(duration / 1000),
              status: task.status || 'completed'
            });
          }
        }
      }
    }

    timeline.sort((a, b) => new Date(a.start) - new Date(b.start));
    res.json({ timeline });
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

// API: Get skills catalog
app.get('/api/skills', (req, res) => {
  try {
    // Load skills from pre-built JSON (generated from core/skills/catalog.py)
    const skillsDataPath = path.join(__dirname, '..', 'config', 'skills.json');
    let skills = [];

    if (fs.existsSync(skillsDataPath)) {
      skills = JSON.parse(fs.readFileSync(skillsDataPath, 'utf-8')).skills || [];
    }

    const { search, type } = req.query;
    let filtered = skills;
    if (search) {
      const q = search.toLowerCase();
      filtered = filtered.filter(s =>
        (s.name || '').toLowerCase().includes(q) ||
        (s.description || '').toLowerCase().includes(q) ||
        (s.category || '').toLowerCase().includes(q)
      );
    }
    if (type) {
      filtered = filtered.filter(s => s.type === type);
    }

    res.json({ skills: filtered, total: filtered.length });
  } catch (error) {
    console.error('Error loading skills:', error);
    res.status(500).json({ error: error.message });
  }
});

// API: Save skill definition (no-op after sub-app removal)
app.put('/api/skills/definition', (req, res) => {
  try {
    const { path: relPath, content } = req.body || {};
    if (!relPath || content === undefined) {
      return res.status(400).json({ error: 'Missing path or content' });
    }

    return res.status(501).json({ error: 'Skill editing requires full install. Skills are managed in core/skills/catalog.py' });
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

// API: Get audit suggestions based on current phase
app.get('/api/audit-suggestions', (req, res) => {
  try {
    const currentPhase = req.query.phase || '0-setup';

    const suggestions = {
      '0-setup': [
        'Configuration Validation',
        'Environment Security Check',
        'API Key Security Audit'
      ],
      '1-discovery': [
        'Corpus Quality Analysis',
        'Feature Extraction Audit',
        'Requirements Completeness Check'
      ],
      '2-prd': [
        'PRD Structure Validation',
        'Requirements Traceability',
        'Dependency Chain Analysis'
      ],
      '5-implementation': [
        'Code Quality Audit',
        'Security Vulnerability Scan',
        'Test Coverage Analysis'
      ]
    };

    res.json({
      phase: currentPhase,
      suggestions: suggestions[currentPhase] || [],
      total_audits: 2186
    });
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

// API: Get audit catalog from pre-built audits.json
let auditCatalogCache = null;
app.get('/api/audits', (req, res) => {
  try {
    if (!auditCatalogCache) {
      const dataPath = path.join(__dirname, '..', 'audits', 'data', 'audits.json');
      if (!fs.existsSync(dataPath)) {
        return res.status(404).json({ error: 'Audit data not found. Expected: audits/data/audits.json' });
      }
      auditCatalogCache = JSON.parse(fs.readFileSync(dataPath, 'utf-8'));
    }

    const { search, tier, category, phase } = req.query;
    let audits = auditCatalogCache.audits || [];

    if (search) {
      const q = search.toLowerCase();
      audits = audits.filter(a =>
        (a.audit_name || '').toLowerCase().includes(q) ||
        (a.audit_id || '').toLowerCase().includes(q) ||
        (a.category || '').toLowerCase().includes(q) ||
        (a.subcategory || '').toLowerCase().includes(q)
      );
    }
    if (tier) {
      audits = audits.filter(a => a.tier === tier);
    }
    if (category) {
      audits = audits.filter(a => a.category === category);
    }
    if (phase) {
      audits = audits.filter(a => a[phase] === true);
    }

    res.json({
      audits,
      navigation: auditCatalogCache.navigation || [],
      stats: auditCatalogCache.stats || {},
      filterOptions: auditCatalogCache.filterOptions || {},
      total: audits.length
    });
  } catch (error) {
    console.error('Error loading audits:', error);
    res.status(500).json({ error: error.message });
  }
});

// API: Proxy to claude-mem localhost (port 37777)
app.get('/api/claude-mem/:endpoint(*)', async (req, res) => {
  try {
    const endpoint = req.params.endpoint;
    const queryString = new URLSearchParams(req.query).toString();
    const url = `http://localhost:37777/api/${endpoint}${queryString ? '?' + queryString : ''}`;

    const response = await fetch(url);
    const data = await response.json();
    res.json(data);
  } catch (error) {
    res.status(503).json({
      error: 'claude-mem not available',
      message: 'Make sure claude-mem is running on localhost:37777'
    });
  }
});

// API: Get AI progress narrative
app.get('/api/narrative', (req, res) => {
  try {
    const statusFile = path.join(STATE_DIR, 'current-task.json');
    if (!fs.existsSync(statusFile)) {
      return res.json({
        narrative: 'No active task. Pipeline is idle.',
        phase: null,
        task: null
      });
    }

    const status = JSON.parse(fs.readFileSync(statusFile, 'utf8'));

    // Generate narrative based on task
    let narrative = `Claude is currently working on ${status.description || 'a task'}. `;

    if (status.provider && status.model) {
      narrative += `Using ${status.provider}/${status.model} for this operation. `;
    }

    narrative += `This task is part of the pipeline's ongoing work.`;

    res.json({
      narrative,
      phase: status.phase || null,
      task: status.task || status.task_id || null,
      model: status.model || null
    });
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

// API: Export pipeline report
app.get('/api/export/report', async (req, res) => {
  try {
    const format = req.query.format || 'json';

    // Gather all data
    const report = {
      generated_at: new Date().toISOString(),
      project: {
        name: 'Unknown Project',
        root: ATOMIC_ROOT
      },
      phases: {},
      metrics: {
        total_tasks: 0,
        completed_tasks: 0,
        failed_tasks: 0
      }
    };

    // Load task state
    const taskStateFile = path.join(STATE_DIR, 'task-state.json');
    if (fs.existsSync(taskStateFile)) {
      const state = JSON.parse(fs.readFileSync(taskStateFile, 'utf8'));
      report.phases = state.phases || {};

      // Calculate metrics
      for (const phase of Object.values(state.phases || {})) {
        for (const task of Object.values(phase.tasks || {})) {
          report.metrics.total_tasks++;
          if (task.status === 'completed') report.metrics.completed_tasks++;
          if (task.status === 'failed') report.metrics.failed_tasks++;
        }
      }
    }

    // Load project name
    const projectConfig = path.join(OUTPUTS_DIR, '0-setup', 'project-config.json');
    if (fs.existsSync(projectConfig)) {
      const config = JSON.parse(fs.readFileSync(projectConfig, 'utf8'));
      report.project.name = config.extracted?.project?.name || config.project?.name || report.project.name;
    }

    // Return based on format
    if (format === 'json') {
      res.json(report);
    } else if (format === 'markdown') {
      const md = generateMarkdownReport(report);
      res.setHeader('Content-Type', 'text/plain');
      res.setHeader('Content-Disposition', 'attachment; filename="pipeline-report.md"');
      res.send(md);
    } else {
      res.status(400).json({ error: 'Unsupported format. Use json or markdown.' });
    }
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

// Helper: Generate markdown report
function generateMarkdownReport(report) {
  let md = `# Pipeline Report: ${report.project.name}\n\n`;
  md += `**Generated:** ${report.generated_at}\n\n`;
  md += `## Metrics\n\n`;
  md += `- Total Tasks: ${report.metrics.total_tasks}\n`;
  md += `- Completed: ${report.metrics.completed_tasks}\n`;
  md += `- Failed: ${report.metrics.failed_tasks}\n`;
  md += `- Success Rate: ${((report.metrics.completed_tasks / report.metrics.total_tasks) * 100).toFixed(1)}%\n\n`;

  md += `## Phases\n\n`;
  for (const [phaseId, phase] of Object.entries(report.phases)) {
    md += `### ${phaseId}\n\n`;
    const tasks = Object.entries(phase.tasks || {});
    md += `Tasks: ${tasks.length}\n\n`;
    for (const [taskId, task] of tasks) {
      const status = task.status === 'completed' ? '✓' : task.status === 'failed' ? '✗' : '○';
      md += `- ${status} Task ${taskId}: ${task.name || 'Unknown'}\n`;
    }
    md += `\n`;
  }

  return md;
}

// ============================================================================
// FalkorDB Graph Queries (Agent Catalog)
// ============================================================================

let redisClient = null;
const GRAPH_HOST = process.env.ATOMIC_GRAPH_HOST || 'localhost';
const GRAPH_PORT = parseInt(process.env.ATOMIC_GRAPH_PORT || '6380');
const GRAPH_NAME = process.env.ATOMIC_GRAPH_NAME || 'atomic-claude';

async function getRedisClient() {
  if (redisClient && redisClient.isOpen) return redisClient;
  redisClient = createClient({ socket: { host: GRAPH_HOST, port: GRAPH_PORT } });
  redisClient.on('error', () => {}); // Suppress connection errors in logs
  await redisClient.connect();
  return redisClient;
}

// Lazy-cached agent name -> path index from manifest
let agentPathIndex = null;
function getAgentPathIndex() {
  if (agentPathIndex) return agentPathIndex;
  try {
    const manifestPath = path.join(ATOMIC_ROOT, 'agents', 'agent-manifest.json');
    const manifest = JSON.parse(fs.readFileSync(manifestPath, 'utf8'));
    agentPathIndex = {};
    for (const a of manifest.agents || []) {
      if (a.name && a.path) agentPathIndex[a.name] = a.path;
    }
  } catch (e) {
    agentPathIndex = {};
  }
  return agentPathIndex;
}

// API: Query Agent nodes from FalkorDB knowledge graph
app.get('/api/agents/graph', async (req, res) => {
  try {
    const client = await getRedisClient();
    const { tier, category, search } = req.query;

    // Build Cypher query with optional filters
    let where = [];
    if (tier) where.push(`n.tier = '${tier.replace(/'/g, "\\'")}'`);
    if (category) where.push(`n.category = '${category.replace(/'/g, "\\'")}'`);
    if (search) {
      const safe = search.replace(/'/g, "\\'");
      where.push(`(toLower(n.name) CONTAINS toLower('${safe}') OR toLower(n.description) CONTAINS toLower('${safe}'))`);
    }

    const whereClause = where.length ? ` WHERE ${where.join(' AND ')}` : '';
    const cypher = `MATCH (n:Agent)${whereClause} RETURN n ORDER BY n.category, n.name`;

    const result = await client.graph.query(GRAPH_NAME, cypher);

    const pathIdx = getAgentPathIndex();
    const agents = result.data.map(row => {
      const node = row.n;
      return {
        name: node.name,
        tier: node.tier,
        category: node.category,
        subcategory: node.subcategory || '',
        role: node.role,
        description: node.description || '',
        grade: node.grade || '',
        composite_score: parseFloat(node.composite_score || 0),
        path: pathIdx[node.name] || '',
      };
    });

    // Group by category for the UI
    const byCategory = {};
    agents.forEach(a => {
      if (!byCategory[a.category]) byCategory[a.category] = [];
      byCategory[a.category].push(a);
    });

    res.json({
      agents,
      total: agents.length,
      byCategory,
      categories: Object.keys(byCategory).sort(),
    });
  } catch (error) {
    // Fall back to manifest file if graph is down
    try {
      const manifestPath = path.join(ATOMIC_ROOT, 'agents', 'agent-manifest.json');
      const manifest = JSON.parse(fs.readFileSync(manifestPath, 'utf8'));
      const agents = manifest.agents || [];
      const byCategory = {};
      agents.forEach(a => {
        const cat = a.category || 'uncategorized';
        if (!byCategory[cat]) byCategory[cat] = [];
        byCategory[cat].push(a);
      });
      res.json({ agents, total: agents.length, byCategory, categories: Object.keys(byCategory).sort(), fallback: true });
    } catch (fallbackError) {
      res.status(500).json({ error: 'Graph unavailable and manifest not found' });
    }
  }
});

// API: Read an agent definition .md file
app.get('/api/agents/definition', (req, res) => {
  try {
    const agentPath = req.query.path;
    if (!agentPath) return res.status(400).json({ error: 'Missing path parameter' });

    const fullPath = path.resolve(path.join(ATOMIC_ROOT, 'agents', agentPath));
    const agentsDir = path.resolve(path.join(ATOMIC_ROOT, 'agents'));
    if (!fullPath.startsWith(agentsDir + path.sep)) {
      return res.status(403).json({ error: 'Access denied' });
    }
    if (!fs.existsSync(fullPath)) {
      return res.status(404).json({ error: 'Agent definition not found' });
    }

    const content = fs.readFileSync(fullPath, 'utf8');
    const stat = fs.statSync(fullPath);
    res.json({ content, size: stat.size, modified: stat.mtime, path: agentPath });
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

// API: Save an edited agent definition .md file
app.put('/api/agents/definition', (req, res) => {
  try {
    const { path: agentPath, content } = req.body;
    if (!agentPath || content === undefined) {
      return res.status(400).json({ error: 'Missing path or content' });
    }

    const fullPath = path.resolve(path.join(ATOMIC_ROOT, 'agents', agentPath));
    const agentsDir = path.resolve(path.join(ATOMIC_ROOT, 'agents'));
    if (!fullPath.startsWith(agentsDir + path.sep)) {
      return res.status(403).json({ error: 'Access denied' });
    }
    if (!fs.existsSync(fullPath)) {
      return res.status(404).json({ error: 'Agent definition not found' });
    }

    fs.writeFileSync(fullPath, content, 'utf8');
    const stat = fs.statSync(fullPath);
    res.json({ success: true, size: stat.size, modified: stat.mtime });
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
