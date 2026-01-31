<script lang="ts">
	import { base } from '$app/paths';
	import AgentEditor from '$lib/components/agent/AgentEditor.svelte';
	import { isStaticBuild, generateIssueUrl, generateGhCommand } from '$lib/config';

	let { data } = $props();

	// In static mode, save always creates an issue
	// In local mode, save writes to filesystem, with optional issue creation
	async function handleSave(content: string) {
		if (isStaticBuild) {
			// Static mode: redirect to GitHub issue
			const url = generateIssueUrl(
				data.agent.frontmatter.name,
				data.agent.relativePath,
				content
			);
			window.open(url, '_blank');
			return;
		}

		// Local mode: save to filesystem
		const response = await fetch(`${base}/api/agents/${data.agent.id}`, {
			method: 'PUT',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify({ content })
		});

		const result = await response.json();

		if (!result.success) {
			throw new Error(result.error || 'Failed to save');
		}
	}

	async function handleCreateIssue(content: string) {
		const url = generateIssueUrl(
			data.agent.frontmatter.name,
			data.agent.relativePath,
			content
		);
		window.open(url, '_blank');
	}

	function handleCopyGhCommand(content: string) {
		const command = generateGhCommand(
			data.agent.frontmatter.name,
			data.agent.relativePath,
			content
		);
		navigator.clipboard.writeText(command);
	}
</script>

<svelte:head>
	<title>Edit {data.agent.frontmatter.name} | Agent Manager</title>
</svelte:head>

<div class="h-[calc(100vh-12rem)]">
	<!-- Static Mode Notice -->
	{#if isStaticBuild}
		<div class="mb-4 p-3 bg-blue-900/30 border border-blue-700/50 rounded-lg">
			<div class="flex items-center gap-2 text-blue-300">
				<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
					<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
				</svg>
				<span class="text-sm font-medium">Static Mode</span>
			</div>
			<p class="text-sm text-gray-400 mt-1">
				Changes will be submitted as a GitHub Issue for review. For direct file editing, clone the repository locally.
			</p>
		</div>
	{/if}

	<!-- Breadcrumbs -->
	<nav class="flex items-center gap-2 text-sm text-gray-400 mb-4">
		<a href="{base}/" class="hover:text-gray-300">Home</a>
		<span>/</span>
		<a href="{base}/agents/{data.agent.category}" class="hover:text-gray-300 capitalize">
			{data.agent.category.replace(/-/g, ' ')}
		</a>
		<span>/</span>
		<a href="{base}/agents/{data.agent.category}/{data.agent.subcategory}" class="hover:text-gray-300 capitalize">
			{data.agent.subcategory.replace(/-/g, ' ')}
		</a>
		<span>/</span>
		<a href="{base}/agents/{data.agent.category}/{data.agent.subcategory}/{data.agent.slug}" class="hover:text-gray-300">
			{data.agent.frontmatter.name}
		</a>
		<span>/</span>
		<span class="text-gray-100">Edit</span>
	</nav>

	<div class="bg-gray-800 rounded-lg border border-gray-700 overflow-hidden h-full">
		<AgentEditor
			agent={data.agent}
			onSave={handleSave}
			onCreateIssue={handleCreateIssue}
			onCopyGhCommand={handleCopyGhCommand}
			staticMode={isStaticBuild}
		/>
	</div>
</div>
