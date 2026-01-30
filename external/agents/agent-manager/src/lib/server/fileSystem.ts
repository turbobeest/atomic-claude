import { readFile, writeFile, readdir, stat } from 'fs/promises';
import { join, relative, basename, dirname } from 'path';
import type { Agent, AgentManifest, NavCategory, NavSubcategory, NavAgent } from '$lib/types';
import { parseAgentFile } from './parser';
import { AGENTS_REPO_PATH } from '$env/static/private';

const REPO_PATH = AGENTS_REPO_PATH || '/mnt/walnut-drive/dev/agents';

// Cache mapping agent ID to file path (populated during navigation build)
const agentPathCache: Map<string, string> = new Map();
let cacheInitialized = false;

/**
 * Ensure the agent path cache is populated
 */
async function ensureCachePopulated(): Promise<void> {
	if (cacheInitialized || agentPathCache.size > 0) return;
	await buildNavigation();
	cacheInitialized = true;
}

/**
 * Load the agent manifest (for reference, but we'll scan directories primarily)
 */
export async function loadManifest(): Promise<AgentManifest> {
	const manifestPath = join(REPO_PATH, 'agent-manifest.json');
	const content = await readFile(manifestPath, 'utf-8');
	return JSON.parse(content);
}

/**
 * Special category name mappings
 */
const CATEGORY_NAME_MAP: Record<string, string> = {
	'00-agent-management': '00 Agent Management',
	'00-orchestration': '00 Orchestration',
	'00-quality-assurance': '00 Quality Assurance',
	'01-ideation': '01 Discovery',
	'02-discovery': '02 PRD',
	'03-validation': '03 Validation',
	'04-audit': '04 Audit',
	'05-task-decomposition': '05 Tasking',
	'06-09-implementation': '06 Build',
	'10-testing': '07 Testing',
	'11-12-deployment': '08 Deployment',
	'signal-processing': 'Military & Defense Systems',
	'backend-ecosystems': 'Languages',
	'blockchain-web3': 'Blockchain'
};

/**
 * Convert folder name to display title
 */
function folderToTitle(folder: string): string {
	const cleanFolder = folder.replace(/^-/, ''); // Remove leading dash

	// Check for special mappings
	if (CATEGORY_NAME_MAP[cleanFolder]) {
		return CATEGORY_NAME_MAP[cleanFolder];
	}

	return cleanFolder
		.split('-')
		.map(word => word.charAt(0).toUpperCase() + word.slice(1))
		.join(' ');
}

/**
 * Clean subcategory name by removing phase number prefixes like "01-02-" or "10-"
 */
function cleanSubcategoryName(folder: string): string {
	const cleanFolder = folder.replace(/^-/, ''); // Remove leading dash
	// Remove phase number prefixes like "01-02-", "03-05-", "10-", "11-12-"
	const withoutPhase = cleanFolder.replace(/^\d{1,2}(-\d{1,2})?-/, '');
	return withoutPhase
		.split('-')
		.map(word => word.charAt(0).toUpperCase() + word.slice(1))
		.join(' ');
}

/**
 * Scan a directory for agent files
 */
async function scanAgentsInDirectory(dirPath: string): Promise<string[]> {
	const agents: string[] = [];

	try {
		const entries = await readdir(dirPath, { withFileTypes: true });

		for (const entry of entries) {
			if (entry.isFile() && entry.name.endsWith('.md')) {
				agents.push(join(dirPath, entry.name));
			}
		}
	} catch {
		// Directory doesn't exist or can't be read
	}

	return agents;
}

/**
 * Scan expert-agents and pipeline-agents directories to build navigation
 */
export async function buildNavigation(): Promise<NavCategory[]> {
	const categories: Map<string, NavCategory> = new Map();

	// Scan both expert-agents and pipeline-agents
	const searchDirs = [
		{ path: join(REPO_PATH, 'expert-agents'), prefix: '' },
		{ path: join(REPO_PATH, 'pipeline-agents'), prefix: 'pipeline-' }
	];

	for (const { path: basePath, prefix } of searchDirs) {
		try {
			const categoryDirs = await readdir(basePath, { withFileTypes: true });

			for (const categoryDir of categoryDirs) {
				if (!categoryDir.isDirectory()) continue;

				const categoryPath = join(basePath, categoryDir.name);
				const categoryId = prefix + categoryDir.name.replace(/^-/, '');
				const categoryTitle = folderToTitle(categoryDir.name);

				// Get or create category
				const isPipeline = prefix !== '';
				let category = categories.get(categoryId);
				if (!category) {
					category = {
						id: categoryId,
						title: categoryTitle,
						description: `${categoryTitle} agents`,
						defaultExpanded: false,
						isPipeline,
						subcategories: []
					};
					categories.set(categoryId, category);
				}

				// Scan subcategories
				const subcategoryDirs = await readdir(categoryPath, { withFileTypes: true });

				// Also check for .md files directly in category directory (not in subcategories)
				const categoryLevelAgents = await scanAgentsInDirectory(categoryPath);
				if (categoryLevelAgents.length > 0) {
					const generalAgents: NavAgent[] = [];
					for (const agentFile of categoryLevelAgents) {
						try {
							const content = await readFile(agentFile, 'utf-8');
							const agent = parseAgentFile(
								agentFile,
								relative(REPO_PATH, agentFile),
								content,
								categoryId,
								'general'
							);

							if (agent && agent.frontmatter) {
								// Cache the agent ID to file path mapping
								agentPathCache.set(agent.id, agent.relativePath);
								generalAgents.push({
									id: agent.id,
									name: agent.frontmatter.name || agent.slug,
									description: agent.frontmatter.description || '',
									tier: agent.frontmatter.tier || 'expert',
									model: agent.frontmatter.model || 'sonnet',
									categoryId,
									subcategoryId: 'general'
								});
							}
						} catch (e) {
							console.error(`Failed to parse agent ${agentFile}:`, e instanceof Error ? e.message : e);
						}
					}

					if (generalAgents.length > 0) {
						const existingGeneral = category.subcategories.find(s => s.id === 'general');
						if (existingGeneral) {
							existingGeneral.agents.push(...generalAgents);
						} else {
							category.subcategories.push({
								id: 'general',
								categoryId,
								title: 'General',
								description: `General ${categoryTitle} specialists`,
								defaultExpanded: false,
								agents: generalAgents
							});
						}
					}
				}

				for (const subcategoryDir of subcategoryDirs) {
					if (!subcategoryDir.isDirectory()) continue;

					const subcategoryPath = join(categoryPath, subcategoryDir.name);
					const subcategoryId = subcategoryDir.name.replace(/^-/, '');
					// Use cleanSubcategoryName for pipeline categories to remove phase prefixes
					const subcategoryTitle = isPipeline
						? cleanSubcategoryName(subcategoryDir.name)
						: folderToTitle(subcategoryDir.name);

					// Scan for agents in this subcategory
					const agentFiles = await scanAgentsInDirectory(subcategoryPath);
					const agents: NavAgent[] = [];

					for (const agentFile of agentFiles) {
						try {
							const content = await readFile(agentFile, 'utf-8');
							const agent = parseAgentFile(
								agentFile,
								relative(REPO_PATH, agentFile),
								content,
								categoryId,
								subcategoryId
							);

							if (agent && agent.frontmatter) {
								// Cache the agent ID to file path mapping
								agentPathCache.set(agent.id, agent.relativePath);
								agents.push({
									id: agent.id,
									name: agent.frontmatter.name || agent.slug,
									description: agent.frontmatter.description || '',
									tier: agent.frontmatter.tier || 'expert',
									model: agent.frontmatter.model || 'sonnet',
									categoryId,
									subcategoryId
								});
							}
						} catch (e) {
							// Skip files that fail to parse
							console.error(`Failed to parse agent ${agentFile}:`, e instanceof Error ? e.message : e);
						}
					}

					// Also check for nested directories (like roster-management/curator/)
					const nestedDirs = await readdir(subcategoryPath, { withFileTypes: true });
					for (const nestedDir of nestedDirs) {
						if (!nestedDir.isDirectory()) continue;

						const nestedPath = join(subcategoryPath, nestedDir.name);
						const nestedAgentFiles = await scanAgentsInDirectory(nestedPath);

						for (const agentFile of nestedAgentFiles) {
							try {
								const content = await readFile(agentFile, 'utf-8');
								const agent = parseAgentFile(
									agentFile,
									relative(REPO_PATH, agentFile),
									content,
									categoryId,
									subcategoryId
								);

								if (agent && agent.frontmatter) {
									// Cache the agent ID to file path mapping
									agentPathCache.set(agent.id, agent.relativePath);
									agents.push({
										id: agent.id,
										name: agent.frontmatter.name || agent.slug,
										description: agent.frontmatter.description || '',
										tier: agent.frontmatter.tier || 'expert',
										model: agent.frontmatter.model || 'sonnet',
										categoryId,
										subcategoryId
									});
								}
							} catch (e) {
								// Skip files that fail to parse
								console.error(`Failed to parse agent ${agentFile}:`, e instanceof Error ? e.message : e);
							}
						}
					}

					if (agents.length > 0) {
						// Check if subcategory already exists
						const existingSubcat = category.subcategories.find(s => s.id === subcategoryId);
						if (existingSubcat) {
							existingSubcat.agents.push(...agents);
						} else {
							category.subcategories.push({
								id: subcategoryId,
								categoryId,
								title: subcategoryTitle,
								description: `${subcategoryTitle} specialists`,
								defaultExpanded: false,
								agents
							});
						}
					}
				}
			}
		} catch (e) {
			console.error(`Failed to scan ${basePath}:`, e);
		}
	}

	// Sort categories and subcategories
	const result = Array.from(categories.values())
		.sort((a, b) => a.title.localeCompare(b.title));

	for (const category of result) {
		category.subcategories.sort((a, b) => a.title.localeCompare(b.title));
		for (const subcategory of category.subcategories) {
			subcategory.agents.sort((a, b) => a.name.localeCompare(b.name));
		}
	}

	return result;
}

/**
 * Find agent file path by searching directories
 */
async function findAgentFile(slug: string, categoryHint?: string, subcategoryHint?: string): Promise<string | null> {
	// Ensure cache is populated
	await ensureCachePopulated();

	// First check the cache if we have category/subcategory hints
	if (categoryHint && subcategoryHint) {
		const agentId = `${categoryHint}/${subcategoryHint}/${slug}`;
		const cachedPath = agentPathCache.get(agentId);
		if (cachedPath) {
			const fullPath = join(REPO_PATH, cachedPath);
			try {
				await stat(fullPath);
				return fullPath;
			} catch {
				// Cache entry invalid, continue with search
			}
		}
	}

	const searchDirs = ['expert-agents', 'pipeline-agents'];

	for (const searchDir of searchDirs) {
		const basePath = join(REPO_PATH, searchDir);

		// If we have hints, try direct path first
		if (categoryHint && subcategoryHint) {
			// Try with and without leading dash
			const paths = [
				join(basePath, categoryHint, subcategoryHint, `${slug}.md`),
				join(basePath, `-${categoryHint}`, subcategoryHint, `${slug}.md`),
				join(basePath, categoryHint, `-${subcategoryHint}`, `${slug}.md`),
				join(basePath, `-${categoryHint}`, `-${subcategoryHint}`, `${slug}.md`),
				// Also try AGENT.md in a folder named after the slug
				join(basePath, categoryHint, subcategoryHint, slug, 'AGENT.md'),
				join(basePath, `-${categoryHint}`, subcategoryHint, slug, 'AGENT.md'),
			];

			for (const path of paths) {
				try {
					await stat(path);
					return path;
				} catch {
					// Not found, try next
				}
			}
		}

		// Fall back to recursive search
		const found = await searchForAgent(basePath, slug);
		if (found) return found;
	}

	return null;
}

/**
 * Recursively search for agent file
 */
async function searchForAgent(dirPath: string, slug: string): Promise<string | null> {
	try {
		const entries = await readdir(dirPath, { withFileTypes: true });

		for (const entry of entries) {
			const fullPath = join(dirPath, entry.name);

			if (entry.isDirectory()) {
				const found = await searchForAgent(fullPath, slug);
				if (found) return found;
			} else if (entry.isFile()) {
				// Match slug.md or AGENT.md in a folder named slug
				if (entry.name === `${slug}.md`) {
					return fullPath;
				}
				if (entry.name === 'AGENT.md' && basename(dirname(fullPath)) === slug) {
					return fullPath;
				}
			}
		}
	} catch {
		// Directory doesn't exist or can't be read
	}

	return null;
}

/**
 * Load agent by slug, category, and subcategory
 */
export async function loadAgentBySlug(
	slug: string,
	categoryId: string,
	subcategoryId: string
): Promise<Agent | null> {
	const filePath = await findAgentFile(slug, categoryId, subcategoryId);

	if (!filePath) {
		return null;
	}

	try {
		const content = await readFile(filePath, 'utf-8');
		return parseAgentFile(
			filePath,
			relative(REPO_PATH, filePath),
			content,
			categoryId,
			subcategoryId
		);
	} catch (e) {
		console.error(`Failed to load agent ${slug}:`, e);
		return null;
	}
}

/**
 * Load agent by full ID (category/subcategory/slug)
 */
export async function loadAgentById(id: string): Promise<Agent | null> {
	const [categoryId, subcategoryId, slug] = id.split('/');
	if (!categoryId || !subcategoryId || !slug) return null;
	return loadAgentBySlug(slug, categoryId, subcategoryId);
}

/**
 * Load all agents by scanning directories
 */
export async function loadAllAgents(): Promise<Agent[]> {
	const navigation = await buildNavigation();
	const agents: Agent[] = [];

	for (const category of navigation) {
		for (const subcategory of category.subcategories) {
			for (const navAgent of subcategory.agents) {
				const slug = navAgent.id.split('/').pop();
				if (slug) {
					const agent = await loadAgentBySlug(slug, category.id, subcategory.id);
					if (agent) {
						agents.push(agent);
					}
				}
			}
		}
	}

	return agents;
}

/**
 * Save agent file
 */
export async function saveAgent(agent: Agent, content: string): Promise<void> {
	await writeFile(agent.filePath, content, 'utf-8');
}

/**
 * Load template file
 */
export async function loadTemplate(tier: 'focused' | 'expert' | 'phd'): Promise<string> {
	const templatePath = join(REPO_PATH, 'templates', `TEMPLATE-${tier}.md`);
	return readFile(templatePath, 'utf-8');
}

/**
 * Check if file exists
 */
export async function fileExists(filePath: string): Promise<boolean> {
	try {
		await stat(filePath);
		return true;
	} catch {
		return false;
	}
}
