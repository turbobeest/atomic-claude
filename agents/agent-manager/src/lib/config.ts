// Build mode configuration
// In static builds, this is set at build time
// In local builds, this defaults to 'local'

export const BUILD_MODE = import.meta.env.VITE_BUILD_MODE || 'local';
export const isStaticBuild = BUILD_MODE === 'static';

// GitHub configuration for issue creation
export const GITHUB_OWNER = import.meta.env.VITE_GITHUB_OWNER || 'turbobeest';
export const GITHUB_REPO = import.meta.env.VITE_GITHUB_REPO || 'agents';
export const GITHUB_ISSUES_URL = `https://github.com/${GITHUB_OWNER}/${GITHUB_REPO}/issues`;

// Generate a pre-filled GitHub issue URL for agent edits
export function generateIssueUrl(
	agentName: string,
	agentPath: string,
	content: string,
	description?: string
): string {
	const title = `[Agent Edit] ${agentName}`;
	const body = `## Agent Update Request

**Agent**: ${agentName}
**Path**: \`${agentPath}\`
**Tier**: ${extractTier(content)}
**Model**: ${extractModel(content)}

### Description
${description || '_Please describe your changes here._'}

### Updated Content
\`\`\`markdown
${content}
\`\`\`

---
_Submitted via Agent Manager_`;

	const params = new URLSearchParams({
		title,
		body,
		labels: 'agent-edit'
	});

	return `${GITHUB_ISSUES_URL}/new?${params.toString()}`;
}

// Generate a gh CLI command for creating an issue
export function generateGhCommand(
	agentName: string,
	agentPath: string,
	content: string
): string {
	const title = `[Agent Edit] ${agentName}`;
	const body = `## Agent Update Request

**Agent**: ${agentName}
**Path**: \\\`${agentPath}\\\`

### Updated Content
\\\`\\\`\\\`markdown
${content.replace(/`/g, '\\`')}
\\\`\\\`\\\``;

	return `gh issue create \\
  --repo ${GITHUB_OWNER}/${GITHUB_REPO} \\
  --title "${title}" \\
  --body "$(cat <<'EOF'
${body}
EOF
)" \\
  --label "agent-edit"`;
}

// Helper to extract tier from content
function extractTier(content: string): string {
	const match = content.match(/^tier:\s*(\w+)/m);
	return match ? match[1] : 'unknown';
}

// Helper to extract model from content
function extractModel(content: string): string {
	const match = content.match(/^model:\s*(\w+)/m);
	return match ? match[1] : 'unknown';
}
