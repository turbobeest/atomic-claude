<script lang="ts">
	import AgentCardSimple from '$lib/components/agent/AgentCardSimple.svelte';
	import { navigation } from '$lib/stores';
	import { goto } from '$app/navigation';
	import { base } from '$app/paths';

	let { data } = $props();

	// Reactive query from load function (updates on client-side navigation)
	let query = $derived(data.query);

	// Local filter state synced from URL params via load
	let selectedTier = $state('');
	let selectedModel = $state('');
	let selectedCategory = $state('');

	// Sync filter state when load data changes (e.g. URL navigation)
	$effect(() => {
		selectedTier = data.tier;
		selectedModel = data.model;
		selectedCategory = data.category;
	});

	// Flatten all agents from navigation store
	let allAgents = $derived(
		$navigation.flatMap((cat) =>
			cat.subcategories.flatMap((sub) =>
				sub.agents.map((agent) => ({
					...agent,
					category: cat.id,
					categoryTitle: cat.title,
					subcategory: sub.id,
					subcategoryTitle: sub.title
				}))
			)
		)
	);

	// Derive unique filter options
	let tierOptions = $derived([...new Set(allAgents.map((a) => a.tier))].sort());
	let modelOptions = $derived([...new Set(allAgents.map((a) => a.model))].sort());
	let categoryOptions = $derived([...new Set(allAgents.map((a) => a.category))].sort());

	// Filter agents client-side
	let filteredAgents = $derived(() => {
		let result = allAgents;

		// Text search from header search bar
		if (query.trim()) {
			const q = query.toLowerCase();
			result = result.filter(
				(a) =>
					a.name.toLowerCase().includes(q) ||
					a.description?.toLowerCase().includes(q) ||
					a.categoryTitle?.toLowerCase().includes(q) ||
					a.subcategoryTitle?.toLowerCase().includes(q)
			);
		}

		// Tier filter
		if (selectedTier) {
			result = result.filter((a) => a.tier === selectedTier);
		}

		// Model filter
		if (selectedModel) {
			result = result.filter((a) => a.model === selectedModel);
		}

		// Category filter
		if (selectedCategory) {
			result = result.filter((a) => a.category === selectedCategory);
		}

		return result;
	});

	let hasActiveFilters = $derived(
		query !== '' || selectedTier !== '' || selectedModel !== '' || selectedCategory !== ''
	);

	function updateFilters() {
		const params = new URLSearchParams();
		if (query) params.set('q', query);
		if (selectedTier) params.set('tier', selectedTier);
		if (selectedModel) params.set('model', selectedModel);
		if (selectedCategory) params.set('category', selectedCategory);
		const qs = params.toString();
		goto(`${base}/search${qs ? '?' + qs : ''}`, { replaceState: true });
	}

	function clearFilters() {
		selectedTier = '';
		selectedModel = '';
		selectedCategory = '';
		goto(`${base}/search`, { replaceState: true });
	}
</script>

<svelte:head>
	<title>{query ? `"${query}" - Search` : 'Search Agents'} | Agent Manager</title>
</svelte:head>

<div>
	<h1 class="text-2xl font-bold text-gray-100 mb-6">
		{#if query}
			Results for "{query}"
		{:else}
			All Agents
		{/if}
		<span class="text-gray-400 font-normal text-lg">({filteredAgents().length})</span>
	</h1>

	<!-- Filters -->
	<div class="bg-gray-800 rounded-lg border border-gray-700 p-4 mb-6">
		<div class="flex items-center gap-4 flex-wrap">
			<div>
				<label for="tier" class="block text-sm font-medium text-gray-300 mb-1">Tier</label>
				<select
					id="tier"
					bind:value={selectedTier}
					onchange={updateFilters}
					class="px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg text-sm text-gray-100"
				>
					<option value="">All tiers</option>
					{#each tierOptions as tier}
						<option value={tier}>{tier}</option>
					{/each}
				</select>
			</div>

			<div>
				<label for="model" class="block text-sm font-medium text-gray-300 mb-1">Model</label>
				<select
					id="model"
					bind:value={selectedModel}
					onchange={updateFilters}
					class="px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg text-sm text-gray-100"
				>
					<option value="">All models</option>
					{#each modelOptions as model}
						<option value={model}>{model}</option>
					{/each}
				</select>
			</div>

			<div>
				<label for="category" class="block text-sm font-medium text-gray-300 mb-1"
					>Category</label
				>
				<select
					id="category"
					bind:value={selectedCategory}
					onchange={updateFilters}
					class="px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg text-sm text-gray-100"
				>
					<option value="">All categories</option>
					{#each categoryOptions as category}
						<option value={category}>{category.replace(/-/g, ' ')}</option>
					{/each}
				</select>
			</div>

			{#if hasActiveFilters}
				<div class="pt-6">
					<button
						type="button"
						onclick={clearFilters}
						class="text-sm text-gray-400 hover:text-gray-300"
					>
						Clear filters
					</button>
				</div>
			{/if}
		</div>
	</div>

	<!-- Results -->
	{#if filteredAgents().length > 0}
		<div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
			{#each filteredAgents() as agent}
				<AgentCardSimple {agent} showCategory={true} />
			{/each}
		</div>
	{:else}
		<div class="text-center py-12 bg-gray-800 rounded-lg border border-gray-700">
			<svg
				class="w-12 h-12 mx-auto text-gray-500 mb-4"
				fill="none"
				stroke="currentColor"
				viewBox="0 0 24 24"
			>
				<path
					stroke-linecap="round"
					stroke-linejoin="round"
					stroke-width="2"
					d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
				/>
			</svg>
			<h3 class="text-lg font-medium text-gray-100 mb-2">No agents found</h3>
			<p class="text-gray-400">Try adjusting your search or filters</p>
		</div>
	{/if}
</div>
