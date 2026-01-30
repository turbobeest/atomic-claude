<script lang="ts">
	import { base } from '$app/paths';
	let { data } = $props();
</script>

<svelte:head>
	<title>{data.category.title} | Agent Manager</title>
</svelte:head>

<div>
	<!-- Breadcrumbs -->
	<nav class="flex items-center gap-2 text-sm text-gray-400 mb-6">
		<a href="{base}/" class="hover:text-gray-300">Home</a>
		<span>/</span>
		<span class="text-gray-100">{data.category.title}</span>
	</nav>

	<div class="bg-gray-800 rounded-lg border border-gray-700 p-6 mb-6">
		<h1 class="text-2xl font-bold text-gray-100 mb-2">{data.category.title}</h1>
		<p class="text-gray-400">{data.category.description}</p>
	</div>

	<div class="grid gap-4">
		{#each data.category.subcategories as subcategory}
			<a
				href="{base}/agents/{data.categoryId}/{subcategory.id}"
				class="block bg-gray-800 rounded-lg border border-gray-700 p-4 hover:border-blue-500 hover:bg-gray-750 transition-all"
			>
				<div class="flex items-center justify-between">
					<div>
						<h2 class="text-lg font-semibold text-gray-100">{subcategory.title}</h2>
						<p class="text-sm text-gray-400 mt-1">{subcategory.description}</p>
					</div>
					<div class="flex items-center gap-2">
						<span class="text-sm text-gray-500">{subcategory.agents.length} agents</span>
						<svg class="w-5 h-5 text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7" />
						</svg>
					</div>
				</div>
			</a>
		{/each}
	</div>
</div>
