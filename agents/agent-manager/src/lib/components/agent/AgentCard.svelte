<script lang="ts">
	import type { Agent } from '$lib/types';
	import { base } from '$app/paths';

	let { agent, showCategory = false }: { agent: Agent; showCategory?: boolean } = $props();

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
	href="{base}/agents/{agent.category}/{agent.subcategory}/{agent.slug}"
	class="block p-4 bg-gray-800 border border-gray-700 rounded-lg hover:border-blue-500 transition-all"
>
	<div class="flex items-start justify-between mb-2">
		<h3 class="text-lg font-semibold text-gray-100 truncate">{agent.frontmatter.name}</h3>
		<div class="flex items-center gap-2">
			<span class="text-xs px-2 py-1 rounded border {getTierColor(agent.frontmatter.tier)}">
				{agent.frontmatter.tier}
			</span>
			<span class="text-xs px-2 py-1 rounded {getModelColor(agent.frontmatter.model)}">
				{agent.frontmatter.model}
			</span>
		</div>
	</div>

	<p class="text-sm text-gray-400 line-clamp-2 mb-3">
		{agent.frontmatter.description}
	</p>

	{#if showCategory}
		<div class="text-xs text-gray-500 mb-2">
			{agent.category} / {agent.subcategory}
		</div>
	{/if}

	{#if agent.content.vocabulary && agent.content.vocabulary.length > 0}
		<div class="flex flex-wrap gap-1">
			{#each agent.content.vocabulary.slice(0, 5) as term}
				<span class="text-xs px-2 py-0.5 bg-gray-700 text-gray-300 rounded">
					{term}
				</span>
			{/each}
			{#if agent.content.vocabulary.length > 5}
				<span class="text-xs px-2 py-0.5 text-gray-500">
					+{agent.content.vocabulary.length - 5} more
				</span>
			{/if}
		</div>
	{/if}

	{#if agent.frontmatter.role}
		<div class="mt-2 flex items-center gap-2 text-xs text-gray-500">
			<svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
				<path
					stroke-linecap="round"
					stroke-linejoin="round"
					stroke-width="2"
					d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z"
				/>
			</svg>
			<span class="capitalize">{agent.frontmatter.role}</span>
		</div>
	{/if}
</a>
