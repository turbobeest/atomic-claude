<script lang="ts">
	import type { NavCategory } from '$lib/types';
	import { sidebarExpanded, sidebarCollapsed } from '$lib/stores';
	import { page } from '$app/stores';
	import { base } from '$app/paths';

	let { categories = [] }: { categories: NavCategory[] } = $props();

	// Separate pipeline categories from regular categories
	let pipelineCategories = $derived(categories.filter((c) => c.isPipeline));
	let regularCategories = $derived(categories.filter((c) => !c.isPipeline));

	function toggleCategory(categoryId: string) {
		sidebarExpanded.update((expanded) => ({
			...expanded,
			[categoryId]: !expanded[categoryId]
		}));
	}

	function toggleSubcategory(subcategoryId: string) {
		sidebarExpanded.update((expanded) => ({
			...expanded,
			[subcategoryId]: !expanded[subcategoryId]
		}));
	}

	function isExpanded(id: string, defaultValue: boolean): boolean {
		return $sidebarExpanded[id] ?? defaultValue;
	}

	function getTierColor(tier: string): string {
		switch (tier) {
			case 'phd':
				return 'bg-purple-900/50 text-purple-300';
			case 'expert':
				return 'bg-blue-900/50 text-blue-300';
			case 'focused':
				return 'bg-green-900/50 text-green-300';
			default:
				return 'bg-gray-700 text-gray-300';
		}
	}
</script>

<aside
	class="bg-gray-800 border-r border-gray-700 overflow-y-auto h-full transition-all duration-300 ease-in-out {$sidebarCollapsed ? 'w-0 opacity-0 overflow-hidden' : 'w-72 opacity-100'}"
>
	<div class="p-4">
		<!-- Pipeline Categories (SDLC Phases, Pipeline Core) -->
		{#if pipelineCategories.length > 0}
			<button
				type="button"
				class="w-full flex items-center justify-between mb-3 group"
				onclick={() => toggleCategory('__pipeline__')}
			>
				<h2 class="text-sm font-semibold text-purple-400 uppercase tracking-wide">Pipeline</h2>
				<svg
					class="w-3.5 h-3.5 text-purple-400 transition-transform {isExpanded('__pipeline__', true) ? 'rotate-90' : ''}"
					fill="none"
					stroke="currentColor"
					viewBox="0 0 24 24"
				>
					<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7" />
				</svg>
			</button>
			{#if isExpanded('__pipeline__', true)}
			<nav class="space-y-1 mb-6">
				{#each pipelineCategories as category}
					{@const isFlatCategory = category.subcategories.length === 1 && category.subcategories[0].id === 'general'}
					{@const flatAgents = isFlatCategory ? category.subcategories[0].agents : []}
					{@const flatSubcategory = isFlatCategory ? category.subcategories[0] : null}
					<div class="mb-2">
						<button
							type="button"
							class="w-full flex items-center justify-between px-3 py-2 text-sm font-medium text-purple-200 rounded-md hover:bg-purple-900/30 transition-colors"
							onclick={() => toggleCategory(category.id)}
						>
							<span class="truncate">{category.title}</span>
							<span class="flex items-center gap-1">
								{#if isFlatCategory}
									<span class="text-xs text-gray-500">{flatAgents.length}</span>
								{/if}
								<svg
									class="w-4 h-4 transition-transform {isExpanded(category.id, category.defaultExpanded)
										? 'rotate-90'
										: ''}"
									fill="none"
									stroke="currentColor"
									viewBox="0 0 24 24"
								>
									<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7" />
								</svg>
							</span>
						</button>

						{#if isExpanded(category.id, category.defaultExpanded)}
							{#if isFlatCategory}
								<!-- Flat: render agents directly under category, skip "General" subcategory -->
								<div class="ml-3 mt-1 space-y-0.5">
									{#each flatAgents as agent}
										<a
											href="{base}/agents/{category.id}/{flatSubcategory?.id}/{agent.id.split('/').pop()}"
											class="flex items-center gap-2 px-3 py-1.5 text-sm rounded transition-colors
												{$page.url.pathname.includes(agent.id.split('/').pop() || '')
												? 'bg-blue-900/50 text-blue-300'
												: 'text-gray-400 hover:bg-gray-700'}"
										>
											<span class="truncate flex-1">{agent.name}</span>
											<span
												class="text-xs px-1.5 py-0.5 rounded {getTierColor(agent.tier)}"
												title={agent.tier}
											>
												{agent.tier.charAt(0).toUpperCase()}
											</span>
										</a>
									{/each}
								</div>
							{:else}
								<!-- Nested: real subcategories exist, show them -->
								<div class="ml-3 mt-1 space-y-1">
									{#each category.subcategories as subcategory}
										<div>
											<button
												type="button"
												class="w-full flex items-center justify-between px-3 py-1.5 text-sm text-gray-400 rounded hover:bg-gray-700 transition-colors"
												onclick={() => toggleSubcategory(subcategory.id)}
											>
												<span class="truncate">{subcategory.title}</span>
												<span class="flex items-center gap-1">
													<span class="text-xs text-gray-500">{subcategory.agents.length}</span>
													<svg
														class="w-3 h-3 transition-transform {isExpanded(
															subcategory.id,
															subcategory.defaultExpanded
														)
															? 'rotate-90'
															: ''}"
														fill="none"
														stroke="currentColor"
														viewBox="0 0 24 24"
													>
														<path
															stroke-linecap="round"
															stroke-linejoin="round"
															stroke-width="2"
															d="M9 5l7 7-7 7"
														/>
													</svg>
												</span>
											</button>

											{#if isExpanded(subcategory.id, subcategory.defaultExpanded)}
												<div class="ml-3 mt-1 space-y-0.5">
													{#each subcategory.agents as agent}
														<a
															href="{base}/agents/{category.id}/{subcategory.id}/{agent.id.split('/').pop()}"
															class="flex items-center gap-2 px-3 py-1.5 text-sm rounded transition-colors
																{$page.url.pathname.includes(agent.id.split('/').pop() || '')
																? 'bg-blue-900/50 text-blue-300'
																: 'text-gray-400 hover:bg-gray-700'}"
														>
															<span class="truncate flex-1">{agent.name}</span>
															<span
																class="text-xs px-1.5 py-0.5 rounded {getTierColor(agent.tier)}"
																title={agent.tier}
															>
																{agent.tier.charAt(0).toUpperCase()}
															</span>
														</a>
													{/each}
												</div>
											{/if}
										</div>
									{/each}
								</div>
							{/if}
						{/if}
					</div>
				{/each}
			</nav>
			{/if}
			<div class="border-t border-gray-700 mb-4"></div>
		{/if}

		<!-- Regular Categories -->
		<h2 class="text-sm font-semibold text-gray-400 uppercase tracking-wide mb-4">Expert Agents</h2>

		<nav class="space-y-1">
			{#each regularCategories as category}
				<div class="mb-2">
					<button
						type="button"
						class="w-full flex items-center justify-between px-3 py-2 text-sm font-medium text-gray-200 rounded-md hover:bg-gray-700 transition-colors"
						onclick={() => toggleCategory(category.id)}
					>
						<span class="truncate">{category.title}</span>
						<svg
							class="w-4 h-4 transition-transform {isExpanded(category.id, category.defaultExpanded)
								? 'rotate-90'
								: ''}"
							fill="none"
							stroke="currentColor"
							viewBox="0 0 24 24"
						>
							<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7" />
						</svg>
					</button>

					{#if isExpanded(category.id, category.defaultExpanded)}
						<div class="ml-3 mt-1 space-y-1">
							{#each category.subcategories as subcategory}
								<div>
									<button
										type="button"
										class="w-full flex items-center justify-between px-3 py-1.5 text-sm text-gray-400 rounded hover:bg-gray-700 transition-colors"
										onclick={() => toggleSubcategory(subcategory.id)}
									>
										<span class="truncate">{subcategory.title}</span>
										<span class="flex items-center gap-1">
											<span class="text-xs text-gray-500">{subcategory.agents.length}</span>
											<svg
												class="w-3 h-3 transition-transform {isExpanded(
													subcategory.id,
													subcategory.defaultExpanded
												)
													? 'rotate-90'
													: ''}"
												fill="none"
												stroke="currentColor"
												viewBox="0 0 24 24"
											>
												<path
													stroke-linecap="round"
													stroke-linejoin="round"
													stroke-width="2"
													d="M9 5l7 7-7 7"
												/>
											</svg>
										</span>
									</button>

									{#if isExpanded(subcategory.id, subcategory.defaultExpanded)}
										<div class="ml-3 mt-1 space-y-0.5">
											{#each subcategory.agents as agent}
												<a
													href="{base}/agents/{category.id}/{subcategory.id}/{agent.id.split('/').pop()}"
													class="flex items-center gap-2 px-3 py-1.5 text-sm rounded transition-colors
														{$page.url.pathname.includes(agent.id.split('/').pop() || '')
														? 'bg-blue-900/50 text-blue-300'
														: 'text-gray-400 hover:bg-gray-700'}"
												>
													<span class="truncate flex-1">{agent.name}</span>
													<span
														class="text-xs px-1.5 py-0.5 rounded {getTierColor(agent.tier)}"
														title={agent.tier}
													>
														{agent.tier.charAt(0).toUpperCase()}
													</span>
												</a>
											{/each}
										</div>
									{/if}
								</div>
							{/each}
						</div>
					{/if}
				</div>
			{/each}
		</nav>
	</div>
</aside>
