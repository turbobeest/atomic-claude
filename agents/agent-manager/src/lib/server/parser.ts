import matter from 'gray-matter';
import type { Agent, AgentFrontmatter, AgentContent } from '$lib/types';
import { basename, dirname } from 'path';

/**
 * Parse an agent markdown file into structured data
 * Handles both YAML frontmatter format and pure markdown format (AGENT.md files)
 */
export function parseAgentFile(
	filePath: string,
	relativePath: string,
	fileContent: string,
	category: string,
	subcategory: string
): Agent {
	// Check if file has YAML frontmatter
	const hasFrontmatter = fileContent.trimStart().startsWith('---');

	let frontmatter: AgentFrontmatter;
	let content: string;

	if (hasFrontmatter) {
		const parsed = matter(fileContent);
		frontmatter = parsed.data as AgentFrontmatter;
		content = parsed.content;
	} else {
		// Parse markdown-only format (AGENT.md files)
		frontmatter = parseMarkdownOnlyFrontmatter(fileContent, filePath);
		content = fileContent;
	}

	const parsedContent = parseMarkdownContent(content);

	// Generate slug from frontmatter name, markdown name, or filename/folder
	let slug = frontmatter.name;
	if (!slug) {
		const filename = basename(filePath, '.md');
		if (filename === 'AGENT') {
			// Use parent folder name for AGENT.md files
			slug = basename(dirname(filePath));
		} else {
			slug = filename;
		}
	}

	// Normalize slug to kebab-case
	slug = slug.toLowerCase().replace(/\s+/g, '-').replace(/[^a-z0-9-]/g, '');

	return {
		id: `${category}/${subcategory}/${slug}`,
		slug,
		filePath,
		relativePath,
		category,
		subcategory,
		frontmatter,
		content: parsedContent,
		rawContent: fileContent,
		rawMarkdown: content
	};
}

/**
 * Parse frontmatter-like data from markdown-only files
 */
function parseMarkdownOnlyFrontmatter(markdown: string, filePath: string): AgentFrontmatter {
	const frontmatter: AgentFrontmatter = {
		name: '',
		description: '',
		tier: 'expert',
		model: 'sonnet'
	};

	// Try to get title from first H1
	const h1Match = markdown.match(/^#\s+(.+)/m);
	if (h1Match) {
		frontmatter.name = h1Match[1].trim();
	}

	// Try to get name from **Name:** pattern in Identity section
	const nameMatch = markdown.match(/\*\*Name:\*\*\s*(.+)/);
	if (nameMatch) {
		frontmatter.name = nameMatch[1].trim();
	}

	// Try to get role from **Role:** pattern
	const roleMatch = markdown.match(/\*\*Role:\*\*\s*(.+)/);
	if (roleMatch) {
		frontmatter.role = roleMatch[1].trim();
	}

	// Try to get description from ## Purpose section
	const purposeMatch = markdown.match(/## Purpose\s*\n([\s\S]*?)(?=\n## |$)/);
	if (purposeMatch) {
		// Get first paragraph
		const firstPara = purposeMatch[1].trim().split('\n\n')[0];
		frontmatter.description = firstPara.replace(/\n/g, ' ').trim();
	}

	// Try to get description from first paragraph after Identity section
	if (!frontmatter.description) {
		const identityMatch = markdown.match(/## Identity\s*\n([\s\S]*?)(?=\n## |$)/);
		if (identityMatch) {
			// Skip the **Name:** etc lines and get first real paragraph
			const lines = identityMatch[1].split('\n').filter(l => !l.startsWith('**'));
			const desc = lines.join(' ').trim();
			if (desc) {
				frontmatter.description = desc.substring(0, 200);
			}
		}
	}

	// Default description if none found
	if (!frontmatter.description) {
		frontmatter.description = `Agent from ${basename(dirname(filePath))}`;
	}

	// Check for tier hints
	if (markdown.toLowerCase().includes('phd') || markdown.toLowerCase().includes('research-grade')) {
		frontmatter.tier = 'phd';
	} else if (markdown.toLowerCase().includes('focused') || markdown.toLowerCase().includes('single-purpose')) {
		frontmatter.tier = 'focused';
	}

	return frontmatter;
}

/**
 * Parse markdown content into structured sections
 */
function parseMarkdownContent(markdown: string): AgentContent {
	const result: AgentContent = {};

	// Extract Identity section
	const identityMatch = markdown.match(/## Identity\s*\n([\s\S]*?)(?=\n## |$)/);
	if (identityMatch) {
		result.identity = identityMatch[1].trim();

		// Extract vocabulary from identity
		const vocabMatch = identityMatch[1].match(/\*\*Vocabulary\*\*:\s*(.+)/);
		if (vocabMatch) {
			result.vocabulary = vocabMatch[1].split(',').map((v) => v.trim());
		}
	}

	// Extract Instructions section
	const instructionsMatch = markdown.match(/## Instructions\s*\n([\s\S]*?)(?=\n## |$)/);
	if (instructionsMatch) {
		result.instructions = parseInstructions(instructionsMatch[1]);
	}

	// Extract Never section
	const neverMatch = markdown.match(/## Never\s*\n([\s\S]*?)(?=\n## |$)/);
	if (neverMatch) {
		result.never = parseListItems(neverMatch[1]);
	}

	// Extract Specializations section
	const specsMatch = markdown.match(/## Specializations\s*\n([\s\S]*?)(?=\n## |$)/);
	if (specsMatch) {
		result.specializations = parseSpecializations(specsMatch[1]);
	}

	// Extract Knowledge Sources section
	const knowledgeMatch = markdown.match(/## Knowledge Sources\s*\n([\s\S]*?)(?=\n## |$)/);
	if (knowledgeMatch) {
		result.knowledgeSources = extractUrls(knowledgeMatch[1]);
	}

	// Extract Output Format section
	const outputMatch = markdown.match(/## Output Format\s*\n([\s\S]*?)(?=\n## |$)/);
	if (outputMatch) {
		result.outputFormat = outputMatch[1].trim();
	}

	return result;
}

/**
 * Parse instructions into categorized lists
 */
function parseInstructions(section: string): AgentContent['instructions'] {
	const instructions: AgentContent['instructions'] = {};

	// Parse "Always" section
	const alwaysMatch = section.match(/### Always[^\n]*\n([\s\S]*?)(?=\n### |$)/);
	if (alwaysMatch) {
		instructions.always = parseNumberedList(alwaysMatch[1]);
	}

	// Parse mode-specific sections
	const modes = ['Generative', 'Critical', 'Evaluative', 'Informative'];
	for (const mode of modes) {
		const modeMatch = section.match(new RegExp(`### When ${mode}[^\\n]*\\n([\\s\\S]*?)(?=\\n### |$)`));
		if (modeMatch) {
			const key = mode.toLowerCase() as keyof typeof instructions;
			instructions[key] = parseNumberedList(modeMatch[1]);
		}
	}

	return instructions;
}

/**
 * Parse a numbered list from markdown
 */
function parseNumberedList(text: string): string[] {
	const items: string[] = [];
	const lines = text.split('\n');

	for (const line of lines) {
		const match = line.match(/^\d+\.\s+(.+)/);
		if (match) {
			items.push(match[1].trim());
		}
	}

	return items;
}

/**
 * Parse bullet list items
 */
function parseListItems(text: string): string[] {
	const items: string[] = [];
	const lines = text.split('\n');

	for (const line of lines) {
		const match = line.match(/^[-*]\s+(.+)/);
		if (match) {
			items.push(match[1].trim());
		}
	}

	return items;
}

/**
 * Parse specializations into a record
 */
function parseSpecializations(section: string): Record<string, string> {
	const specs: Record<string, string> = {};
	const parts = section.split(/### /);

	for (const part of parts) {
		if (!part.trim()) continue;
		const lines = part.split('\n');
		const title = lines[0].trim();
		const content = lines.slice(1).join('\n').trim();
		if (title) {
			specs[title] = content;
		}
	}

	return specs;
}

/**
 * Extract URLs from text
 */
function extractUrls(text: string): string[] {
	const urlRegex = /https?:\/\/[^\s)]+/g;
	return text.match(urlRegex) || [];
}

/**
 * Serialize an agent back to markdown format
 */
export function serializeAgent(agent: Agent): string {
	const frontmatterStr = matter.stringify('', agent.frontmatter);
	return frontmatterStr + agent.rawMarkdown;
}

/**
 * Update agent frontmatter while preserving markdown content
 */
export function updateAgentFrontmatter(
	agent: Agent,
	updates: Partial<AgentFrontmatter>
): string {
	const newFrontmatter = { ...agent.frontmatter, ...updates };
	return matter.stringify(agent.rawMarkdown, newFrontmatter);
}

/**
 * Generate a diff between two agent versions
 */
export function generateDiff(original: string, modified: string): string {
	const origLines = original.split('\n');
	const modLines = modified.split('\n');
	const diff: string[] = [];

	const maxLen = Math.max(origLines.length, modLines.length);

	for (let i = 0; i < maxLen; i++) {
		const origLine = origLines[i] || '';
		const modLine = modLines[i] || '';

		if (origLine !== modLine) {
			if (origLine) diff.push(`- ${origLine}`);
			if (modLine) diff.push(`+ ${modLine}`);
		}
	}

	return diff.join('\n');
}
