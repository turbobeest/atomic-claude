// @ts-nocheck
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const SKILLS_ROOT = path.resolve(__dirname, '..', '..', '..');

/**
 * Parse a README.md file and extract name, description, author.
 */
function parseReadme(content, dirName, category, type) {
  try {
    const lines = content.split('\n');

    // Extract title from first # heading
    let name = dirName.replace(/-/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
    for (const line of lines) {
      const headingMatch = line.match(/^#\s+(.+)/);
      if (headingMatch) {
        name = headingMatch[1].trim();
        break;
      }
    }

    // Extract description: first non-empty paragraph after the heading
    let description = '';
    let pastHeading = false;
    for (const line of lines) {
      if (line.startsWith('# ')) {
        pastHeading = true;
        continue;
      }
      if (!pastHeading) continue;

      // Skip badges, blank lines, blockquotes used as taglines
      const trimmed = line.trim();
      if (!trimmed) continue;
      if (trimmed.startsWith('[![')) continue;
      if (trimmed.startsWith('![')) continue;

      // Use blockquote taglines as description
      if (trimmed.startsWith('> ')) {
        description = trimmed.replace(/^>\s*\**/, '').replace(/\**$/, '').trim();
        break;
      }

      // Skip author lines
      if (trimmed.startsWith('**Author:**')) continue;

      // First real paragraph text
      if (trimmed.startsWith('#') || trimmed.startsWith('|') || trimmed.startsWith('```')) break;
      description = trimmed;
      break;
    }

    // Extract author
    let author = '';
    for (const line of lines) {
      const authorMatch = line.match(/\*\*Author:\*\*\s*(.+)/);
      if (authorMatch) {
        author = authorMatch[1].trim();
        break;
      }
    }

    // Extract "When to Use" or "What It Does" section for tags
    const tags = [];
    const whenMatch = content.match(/## When to Use\n\n([\s\S]*?)(?=\n##|\n$)/);
    if (whenMatch) {
      const bullets = whenMatch[1].match(/^[-*]\s+(.+)/gm);
      if (bullets) {
        bullets.slice(0, 3).forEach(b => {
          tags.push(b.replace(/^[-*]\s+/, '').slice(0, 60));
        });
      }
    }

    return {
      id: `${type}-${category}-${dirName}`,
      name,
      description,
      author,
      category,
      type,
      tags,
      dirName
    };
  } catch {
    return null;
  }
}

/**
 * Scan a directory for subdirectories containing README.md files.
 */
function scanSkillDirs(parentDir, category, type) {
  const skills = [];
  if (!fs.existsSync(parentDir)) return skills;

  const dirs = fs.readdirSync(parentDir).filter(f => {
    try {
      return fs.statSync(path.join(parentDir, f)).isDirectory();
    } catch { return false; }
  });

  for (const dir of dirs) {
    const readmePath = path.join(parentDir, dir, 'README.md');
    if (fs.existsSync(readmePath)) {
      const content = fs.readFileSync(readmePath, 'utf-8');
      const skill = parseReadme(content, dir, category, type);
      if (skill) skills.push(skill);
    } else {
      // Directory without README — create minimal entry from directory name
      skills.push({
        id: `${type}-${category}-${dir}`,
        name: dir.replace(/-/g, ' ').replace(/\b\w/g, c => c.toUpperCase()),
        description: '',
        author: '',
        category,
        type,
        tags: [],
        dirName: dir
      });
    }
  }
  return skills;
}

/** */
export function load() {
  const skills = [];

  // Scan tactical skills: tactical/{category}/{skill}/
  const tacticalDir = path.join(SKILLS_ROOT, 'tactical');
  if (fs.existsSync(tacticalDir)) {
    const categories = fs.readdirSync(tacticalDir).filter(f => {
      try {
        return fs.statSync(path.join(tacticalDir, f)).isDirectory();
      } catch { return false; }
    });

    for (const category of categories) {
      skills.push(...scanSkillDirs(path.join(tacticalDir, category), category, 'tactical'));
    }
  }

  // Scan community skills - superpowers: community/superpowers/skills/{skill}/
  const superpowersDir = path.join(SKILLS_ROOT, 'community', 'superpowers', 'skills');
  skills.push(...scanSkillDirs(superpowersDir, 'superpowers', 'community'));

  // Scan community skills - trailofbits: community/trailofbits/plugins/{plugin}/
  const trailofbitsDir = path.join(SKILLS_ROOT, 'community', 'trailofbits', 'plugins');
  skills.push(...scanSkillDirs(trailofbitsDir, 'trailofbits', 'community'));

  // Scan community skills - ralph: community/ralph/ (single entry)
  const ralphDir = path.join(SKILLS_ROOT, 'community', 'ralph');
  if (fs.existsSync(ralphDir)) {
    const readmePath = path.join(ralphDir, 'README.md');
    if (fs.existsSync(readmePath)) {
      const content = fs.readFileSync(readmePath, 'utf-8');
      const skill = parseReadme(content, 'ralph', 'ralph', 'community');
      if (skill) skills.push(skill);
    }
  }

  return { skills };
}
