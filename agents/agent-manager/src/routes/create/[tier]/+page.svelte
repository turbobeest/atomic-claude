<script lang="ts">
	import { marked } from 'marked';
	import { goto } from '$app/navigation';
	import { base } from '$app/paths';

	let { data } = $props();

	let content = $state(data.template);
	let showPreview = $state(true);
	let agentName = $state('');
	let selectedCategory = $state('');
	let selectedSubcategory = $state('');
	let isSaving = $state(false);
	let error = $state<string | null>(null);

	let subcategories = $derived(
		selectedCategory
			? data.categories.find((c) => c.id === selectedCategory)?.subcategories || []
			: []
	);

	function handleInput(e: Event) {
		content = (e.target as HTMLTextAreaElement).value;
	}

	function renderPreview(): string {
		const parts = content.split('---');
		if (parts.length >= 3) {
			const markdown = parts.slice(2).join('---');
			return marked(markdown) as string;
		}
		return marked(content) as string;
	}

	async function handleCreate() {
		if (!agentName.trim()) {
			error = 'Agent name is required';
			return;
		}
		if (!selectedCategory || !selectedSubcategory) {
			error = 'Category and subcategory are required';
			return;
		}

		isSaving = true;
		error = null;

		// Replace placeholders in template
		const finalContent = content
			.replace('{agent-name}', agentName.toLowerCase().replace(/\s+/g, '-'))
			.replace(/{Agent Name}/g, agentName);

		try {
			const response = await fetch(`${base}/api/agents/create`, {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({
					name: agentName.toLowerCase().replace(/\s+/g, '-'),
					category: selectedCategory,
					subcategory: selectedSubcategory,
					content: finalContent
				})
			});

			const result = await response.json();

			if (result.success) {
				goto(`${base}/agents/${selectedCategory}/${selectedSubcategory}/${agentName.toLowerCase().replace(/\s+/g, '-')}`);
			} else {
				error = result.error || 'Failed to create agent';
			}
		} catch (e) {
			error = e instanceof Error ? e.message : 'Failed to create agent';
		} finally {
			isSaving = false;
		}
	}

	function getTierColor(tier: string): string {
		switch (tier) {
			case 'phd': return 'bg-purple-900/50 text-purple-300';
			case 'expert': return 'bg-blue-900/50 text-blue-300';
			case 'focused': return 'bg-green-900/50 text-green-300';
			default: return 'bg-gray-700 text-gray-300';
		}
	}
</script>

<svelte:head>
	<title>Create {data.tier} Agent | Agent Manager</title>
</svelte:head>

<div class="h-[calc(100vh-12rem)]">
	<!-- Header -->
	<div class="flex items-center justify-between mb-4">
		<div class="flex items-center gap-3">
			<a href="{base}/create" class="text-gray-400 hover:text-gray-300">
				<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
					<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7" />
				</svg>
			</a>
			<h1 class="text-xl font-bold text-gray-100">Create New Agent</h1>
			<span class="px-2 py-1 text-sm rounded {getTierColor(data.tier)}">{data.tier}</span>
		</div>

		<button
			type="button"
			class="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors disabled:opacity-50"
			onclick={handleCreate}
			disabled={isSaving}
		>
			{isSaving ? 'Creating...' : 'Create Agent'}
		</button>
	</div>

	{#if error}
		<div class="mb-4 p-3 bg-red-900/50 border border-red-700 text-red-300 rounded-lg">
			{error}
		</div>
	{/if}

	<!-- Form -->
	<div class="bg-gray-800 rounded-lg border border-gray-700 p-4 mb-4">
		<div class="grid grid-cols-3 gap-4">
			<div>
				<label for="name" class="block text-sm font-medium text-gray-300 mb-1">Agent Name</label>
				<input
					id="name"
					type="text"
					bind:value={agentName}
					placeholder="e.g., rust-safety-validator"
					class="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg text-gray-100 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500"
				/>
			</div>

			<div>
				<label for="category" class="block text-sm font-medium text-gray-300 mb-1">Category</label>
				<select
					id="category"
					bind:value={selectedCategory}
					class="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg text-gray-100 focus:outline-none focus:ring-2 focus:ring-blue-500"
				>
					<option value="">Select category</option>
					{#each data.categories as category}
						<option value={category.id}>{category.title}</option>
					{/each}
				</select>
			</div>

			<div>
				<label for="subcategory" class="block text-sm font-medium text-gray-300 mb-1">Subcategory</label>
				<select
					id="subcategory"
					bind:value={selectedSubcategory}
					disabled={!selectedCategory}
					class="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg text-gray-100 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:bg-gray-600 disabled:text-gray-400"
				>
					<option value="">Select subcategory</option>
					{#each subcategories as subcategory}
						<option value={subcategory.id}>{subcategory.title}</option>
					{/each}
				</select>
			</div>
		</div>
	</div>

	<!-- Editor -->
	<div class="bg-gray-800 rounded-lg border border-gray-700 overflow-hidden h-[calc(100%-12rem)]">
		<div class="flex items-center justify-between p-2 border-b border-gray-700 bg-gray-800">
			<span class="text-sm font-medium text-gray-300">Template Editor</span>
			<button
				type="button"
				class="px-3 py-1 text-sm {showPreview ? 'bg-gray-600' : 'bg-gray-700'} text-gray-200 border border-gray-600 rounded hover:bg-gray-600"
				onclick={() => (showPreview = !showPreview)}
			>
				{showPreview ? 'Hide Preview' : 'Show Preview'}
			</button>
		</div>

		<div class="flex h-[calc(100%-2.5rem)] overflow-hidden">
			<div class={showPreview ? 'w-1/2' : 'w-full'}>
				<textarea
					class="w-full h-full p-4 font-mono text-sm resize-none focus:outline-none bg-gray-900 text-gray-100"
					value={content}
					oninput={handleInput}
					spellcheck="false"
				></textarea>
			</div>

			{#if showPreview}
				<div class="w-1/2 border-l border-gray-700 overflow-y-auto bg-gray-800">
					<div class="p-6 prose prose-sm prose-invert max-w-none">
						{@html renderPreview()}
					</div>
				</div>
			{/if}
		</div>
	</div>
</div>
