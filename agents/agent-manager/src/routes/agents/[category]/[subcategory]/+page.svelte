<script lang="ts">
	import { base } from '$app/paths';
	import AgentCard from '$lib/components/agent/AgentCard.svelte';

	let { data } = $props();
</script>

<svelte:head>
	<title>{data.subcategory.title} | {data.category.title} | Agent Manager</title>
</svelte:head>

<div>
	<!-- Breadcrumbs -->
	<nav class="flex items-center gap-2 text-sm text-gray-400 mb-6">
		<a href="{base}/" class="hover:text-gray-300">Home</a>
		<span>/</span>
		<a href="{base}/agents/{data.categoryId}" class="hover:text-gray-300">{data.category.title}</a>
		<span>/</span>
		<span class="text-gray-100">{data.subcategory.title}</span>
	</nav>

	<div class="bg-gray-800 rounded-lg border border-gray-700 p-6 mb-6">
		<h1 class="text-2xl font-bold text-gray-100 mb-2">{data.subcategory.title}</h1>
		<p class="text-gray-400">{data.subcategory.description}</p>
		<p class="text-sm text-gray-500 mt-2">{data.agents.length} agents</p>
	</div>

	<div class="grid grid-cols-2 gap-4">
		{#each data.agents as agent}
			<AgentCard {agent} />
		{/each}
	</div>

	{#if data.agents.length === 0}
		<div class="text-center py-12 text-gray-400">
			<p>No agents found in this subcategory.</p>
		</div>
	{/if}
</div>
