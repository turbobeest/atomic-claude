<script lang="ts">
	import { base } from '$app/paths';

	interface SimpleAgent {
		name: string;
		description?: string;
		tier: string;
		model: string;
		id?: string;
		slug?: string;
		category: string;
		subcategory: string;
		categoryTitle?: string;
		subcategoryTitle?: string;
	}

	let { agent, showCategory = true }: { agent: SimpleAgent; showCategory?: boolean } = $props();

	// Support both 'slug' and 'id' as the agent identifier
	let agentSlug = $derived(agent.slug || agent.id || agent.name);

	function getTierColor(tier: string): string {
		switch (tier) {
			case 'phd':
				return 'bg-purple-900/50 text-purple-300 border-purple-700';
			case 'expert':
				return 'bg-blue-900/50 text-blue-300 border-blue-700';
			case 'focused':
				return 'bg-green-900/50 text-green-300 border-green-700';
			default:
				return 'bg-gray-700 text-gray-300 border-gray-600';
		}
	}

	function getModelColor(model: string): string {
		switch (model) {
			case 'opus':
				return 'bg-orange-900/50 text-orange-300';
			case 'sonnet':
				return 'bg-indigo-900/50 text-indigo-300';
			case 'haiku':
				return 'bg-teal-900/50 text-teal-300';
			default:
				return 'bg-gray-700 text-gray-300';
		}
	}
</script>

<a
	href="{base}/agents/{agent.category}/{agent.subcategory}/{agentSlug}"
	class="block p-4 bg-gray-800 border border-gray-700 rounded-lg hover:border-blue-500 hover:bg-gray-750 transition-all"
>
	<div class="flex items-start justify-between gap-2 mb-2">
		<h3 class="text-base font-semibold text-gray-100 truncate flex-1">{agent.name}</h3>
		<div class="flex items-center gap-1.5 flex-shrink-0">
			<span class="text-xs px-1.5 py-0.5 rounded border {getTierColor(agent.tier)}">
				{agent.tier}
			</span>
			<span class="text-xs px-1.5 py-0.5 rounded {getModelColor(agent.model)}">
				{agent.model}
			</span>
		</div>
	</div>

	{#if agent.description}
		<p class="text-sm text-gray-400 line-clamp-2 mb-2">
			{agent.description}
		</p>
	{/if}

	{#if showCategory && (agent.categoryTitle || agent.subcategoryTitle)}
		<div class="text-xs text-gray-500">
			{agent.categoryTitle || agent.category} / {agent.subcategoryTitle || agent.subcategory}
		</div>
	{/if}
</a>
