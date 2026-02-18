import { Octokit } from '@octokit/rest';
import { exec } from 'child_process';
import { promisify } from 'util';
import type { GitStatus, GitHubIssue, SyncStatus, Agent } from '$lib/types';
import { AGENTS_REPO_PATH } from '$env/static/private';

const execAsync = promisify(exec);
const REPO_PATH = AGENTS_REPO_PATH || '/mnt/walnut-drive/dev/agents';

// GitHub configuration - all optional with sensible defaults
const GITHUB_TOKEN = process.env.GITHUB_TOKEN || '';
const GITHUB_OWNER = process.env.GITHUB_OWNER || process.env.VITE_GITHUB_OWNER || 'turbobeest';
const GITHUB_REPO = process.env.GITHUB_REPO || process.env.VITE_GITHUB_REPO || 'agents';

/**
 * Get Octokit instance with authentication
 */
function getOctokit(accessToken?: string): Octokit | null {
	const token = accessToken || GITHUB_TOKEN;
	if (!token) return null;
	return new Octokit({ auth: token });
}

/**
 * Execute git command in repo directory
 */
async function git(command: string): Promise<string> {
	const { stdout } = await execAsync(`git ${command}`, { cwd: REPO_PATH });
	return stdout.trim();
}

/**
 * Get current git status
 */
export async function getGitStatus(): Promise<GitStatus> {
	try {
		// Get current branch
		const currentBranch = await git('branch --show-current');

		// Fetch from remote (without pulling)
		try {
			await git('fetch --quiet');
		} catch {
			// Fetch might fail if offline
		}

		// Check for local changes
		const statusOutput = await git('status --porcelain');
		const localChanges = statusOutput.split('\n').filter((line) => line.trim());

		// Check for remote changes
		let remoteChanges: string[] = [];
		let status: SyncStatus = 'synced';

		try {
			const behind = await git(`rev-list HEAD..origin/${currentBranch} --count`);
			const ahead = await git(`rev-list origin/${currentBranch}..HEAD --count`);

			const behindCount = parseInt(behind) || 0;
			const aheadCount = parseInt(ahead) || 0;

			if (behindCount > 0) {
				const remoteDiff = await git(
					`diff --name-only HEAD..origin/${currentBranch}`
				);
				remoteChanges = remoteDiff.split('\n').filter((line) => line.trim());
			}

			if (localChanges.length > 0 && remoteChanges.length > 0) {
				status = 'conflict';
			} else if (localChanges.length > 0) {
				status = 'local-changes';
			} else if (behindCount > 0) {
				status = 'remote-changes';
			} else {
				status = 'synced';
			}
		} catch {
			status = localChanges.length > 0 ? 'local-changes' : 'unknown';
		}

		return {
			status,
			localChanges,
			remoteChanges,
			currentBranch,
			lastFetch: new Date()
		};
	} catch (error) {
		console.error('Git status error:', error);
		return {
			status: 'unknown',
			localChanges: [],
			remoteChanges: [],
			currentBranch: 'unknown'
		};
	}
}

/**
 * Pull remote changes (with stash if needed)
 */
export async function pullChanges(): Promise<{ success: boolean; message: string }> {
	try {
		const status = await getGitStatus();

		// Stash local changes if any
		let stashed = false;
		if (status.localChanges.length > 0) {
			await git('stash push -m "agent-manager-auto-stash"');
			stashed = true;
		}

		// Pull changes
		const pullOutput = await git('pull --rebase');

		// Pop stash if we stashed
		if (stashed) {
			try {
				await git('stash pop');
			} catch {
				return {
					success: false,
					message: 'Pull succeeded but stash pop failed. Check for conflicts.'
				};
			}
		}

		return { success: true, message: pullOutput };
	} catch (error) {
		return {
			success: false,
			message: error instanceof Error ? error.message : 'Pull failed'
		};
	}
}

/**
 * Create GitHub issue for agent change
 */
export async function createAgentIssue(
	accessToken: string,
	agent: Agent,
	changeType: 'edit' | 'create',
	diff: string,
	description?: string
): Promise<GitHubIssue | null> {
	const octokit = getOctokit(accessToken);
	if (!octokit) return null;

	const title =
		changeType === 'create'
			? `[New Agent] ${agent.frontmatter.name}`
			: `[Edit] ${agent.frontmatter.name}`;

	const body = `## Agent ${changeType === 'create' ? 'Creation' : 'Edit'} Request

**Agent**: ${agent.frontmatter.name}
**Tier**: ${agent.frontmatter.tier}
**Model**: ${agent.frontmatter.model}
**Path**: \`${agent.relativePath}\`

### Description
${description || 'No description provided'}

### Changes
\`\`\`diff
${diff}
\`\`\`

---
*Created via Agent Manager*
`;

	try {
		const { data } = await octokit.issues.create({
			owner: GITHUB_OWNER,
			repo: GITHUB_REPO,
			title,
			body,
			labels: ['agent-change', changeType, agent.frontmatter.tier]
		});

		return {
			id: data.id,
			number: data.number,
			title: data.title,
			body: data.body || '',
			state: data.state as 'open' | 'closed',
			html_url: data.html_url,
			created_at: data.created_at,
			labels: data.labels.map((l) =>
				typeof l === 'string' ? { name: l } : { name: l.name || '' }
			)
		};
	} catch (error) {
		console.error('Failed to create issue:', error);
		return null;
	}
}

/**
 * Get pending issues for an agent
 */
export async function getAgentIssues(
	accessToken: string,
	agentName: string
): Promise<GitHubIssue[]> {
	const octokit = getOctokit(accessToken);
	if (!octokit) return [];

	try {
		const { data } = await octokit.issues.listForRepo({
			owner: GITHUB_OWNER,
			repo: GITHUB_REPO,
			state: 'open',
			labels: 'agent-change'
		});

		return data
			.filter((issue) => issue.title.includes(agentName))
			.map((issue) => ({
				id: issue.id,
				number: issue.number,
				title: issue.title,
				body: issue.body || '',
				state: issue.state as 'open' | 'closed',
				html_url: issue.html_url,
				created_at: issue.created_at,
				labels: issue.labels.map((l) =>
					typeof l === 'string' ? { name: l } : { name: l.name || '' }
				)
			}));
	} catch (error) {
		console.error('Failed to get issues:', error);
		return [];
	}
}

/**
 * Get all pending agent change issues
 */
export async function getAllPendingIssues(accessToken: string): Promise<GitHubIssue[]> {
	const octokit = getOctokit(accessToken);
	if (!octokit) return [];

	try {
		const { data } = await octokit.issues.listForRepo({
			owner: GITHUB_OWNER,
			repo: GITHUB_REPO,
			state: 'open',
			labels: 'agent-change',
			per_page: 100
		});

		return data.map((issue) => ({
			id: issue.id,
			number: issue.number,
			title: issue.title,
			body: issue.body || '',
			state: issue.state as 'open' | 'closed',
			html_url: issue.html_url,
			created_at: issue.created_at,
			labels: issue.labels.map((l) =>
				typeof l === 'string' ? { name: l } : { name: l.name || '' }
			)
		}));
	} catch {
		return [];
	}
}

/**
 * Exchange OAuth code for access token
 */
export async function exchangeCodeForToken(
	code: string,
	clientId: string,
	clientSecret: string
): Promise<string | null> {
	try {
		const response = await fetch('https://github.com/login/oauth/access_token', {
			method: 'POST',
			headers: {
				'Content-Type': 'application/json',
				Accept: 'application/json'
			},
			body: JSON.stringify({
				client_id: clientId,
				client_secret: clientSecret,
				code
			})
		});

		const data = await response.json();
		return data.access_token || null;
	} catch {
		return null;
	}
}

/**
 * Get authenticated user info
 */
export async function getUser(accessToken: string): Promise<{ login: string; avatar_url: string } | null> {
	const octokit = getOctokit(accessToken);
	if (!octokit) return null;

	try {
		const { data } = await octokit.users.getAuthenticated();
		return { login: data.login, avatar_url: data.avatar_url };
	} catch {
		return null;
	}
}
