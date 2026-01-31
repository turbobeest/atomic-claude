<script lang="ts">
	import { base } from '$app/paths';
	import AgentDetail from '$lib/components/agent/AgentDetail.svelte';

	let { data } = $props();
</script>

<svelte:head>
	<title>{data.agent.frontmatter.name} | Agent Manager</title>
	<meta name="description" content={data.agent.frontmatter.description} />
</svelte:head>

<div class="w-full">
	<!-- Breadcrumbs -->
	<nav class="flex items-center gap-2 text-sm text-gray-400 mb-6">
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
		<span class="text-gray-100">{data.agent.frontmatter.name}</span>
	</nav>

	<AgentDetail agent={data.agent} />
</div>
