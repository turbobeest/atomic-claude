<script lang="ts">
	import type { Agent } from '$lib/types';
	import { marked } from 'marked';
	import { saveDraftToStorage, loadDraftFromStorage, clearDraftFromStorage } from '$lib/stores';

	let { agent }: { agent: Agent } = $props();

	let activeTab = $state('overview');
	let isEditMode = $state(false);
	let editContent = $state(agent.rawContent);
	let isDirty = $state(false);
	let isSaving = $state(false);
	let saveError = $state<string | null>(null);
	let saveSuccess = $state(false);

	// Resizable panel state
	let splitPercent = $state(65);
	let isResizing = $state(false);
	let containerRef = $state<HTMLDivElement | null>(null);

	// Check for saved draft when entering edit mode
	$effect(() => {
		if (isEditMode) {
			const draft = loadDraftFromStorage(agent.id);
			if (draft && draft !== agent.rawContent) {
				const useDraft = confirm('A draft was found for this agent. Do you want to restore it?');
				if (useDraft) {
					editContent = draft;
					isDirty = true;
				}
			}
		}
	});

	// Auto-save draft when editing
	$effect(() => {
		if (isEditMode && isDirty) {
			saveDraftToStorage(agent.id, editContent);
		}
	});

	function toggleEditMode() {
		if (isEditMode && isDirty) {
			const confirmed = confirm('You have unsaved changes. Discard them?');
			if (!confirmed) return;
			editContent = agent.rawContent;
			isDirty = false;
			clearDraftFromStorage(agent.id);
		}
		isEditMode = !isEditMode;
		saveSuccess = false;
		saveError = null;
	}

	function handleInput(e: Event) {
		const target = e.target as HTMLTextAreaElement;
		editContent = target.value;
		isDirty = editContent !== agent.rawContent;
		saveSuccess = false;
	}

	async function handleSave() {
		if (!isDirty) return;

		isSaving = true;
		saveError = null;
		saveSuccess = false;

		try {
			const response = await fetch(`/api/agents/${agent.category}/${agent.subcategory}/${agent.slug}`, {
				method: 'PUT',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({ content: editContent })
			});

			if (!response.ok) {
				const data = await response.json();
				throw new Error(data.error || 'Failed to save');
			}

			isDirty = false;
			saveSuccess = true;
			clearDraftFromStorage(agent.id);

			// Update the agent's raw content
			agent.rawContent = editContent;

			// Auto-hide success message after 3 seconds
			setTimeout(() => {
				saveSuccess = false;
			}, 3000);
		} catch (error) {
			saveError = error instanceof Error ? error.message : 'Failed to save';
		} finally {
			isSaving = false;
		}
	}

	function handleReset() {
		if (isDirty) {
			const confirmed = confirm('Discard all changes?');
			if (!confirmed) return;
		}
		editContent = agent.rawContent;
		isDirty = false;
		saveError = null;
		clearDraftFromStorage(agent.id);
	}

	// Keyboard shortcuts
	function handleKeydown(e: KeyboardEvent) {
		if (isEditMode && (e.metaKey || e.ctrlKey) && e.key === 's') {
			e.preventDefault();
			handleSave();
		}
		if (e.key === 'Escape' && isEditMode) {
			toggleEditMode();
		}
	}

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

	function renderMarkdown(content: string): string {
		return marked(content) as string;
	}

	function renderEditPreview(): string {
		const parts = editContent.split('---');
		if (parts.length >= 3) {
			const markdown = parts.slice(2).join('---');
			return marked(markdown) as string;
		}
		return marked(editContent) as string;
	}

	const tabs = [
		{ id: 'overview', label: 'Overview' },
		{ id: 'instructions', label: 'Instructions' },
		{ id: 'specializations', label: 'Specializations' },
		{ id: 'config', label: 'Configuration' },
		{ id: 'raw', label: 'Raw' }
	];

	function handleExport() {
		const filename = `${agent.frontmatter.name}.md`;
		const blob = new Blob([agent.rawContent], { type: 'text/markdown' });
		const url = URL.createObjectURL(blob);
		const a = document.createElement('a');
		a.href = url;
		a.download = filename;
		document.body.appendChild(a);
		a.click();
		document.body.removeChild(a);
		URL.revokeObjectURL(url);
	}

	// Resizer drag handlers
	function handleResizeStart(e: MouseEvent) {
		e.preventDefault();
		isResizing = true;
		document.addEventListener('mousemove', handleResizeMove);
		document.addEventListener('mouseup', handleResizeEnd);
	}

	function handleResizeMove(e: MouseEvent) {
		if (!isResizing || !containerRef) return;
		const rect = containerRef.getBoundingClientRect();
		const newPercent = ((e.clientX - rect.left) / rect.width) * 100;
		// Clamp between 20% and 80%
		splitPercent = Math.max(20, Math.min(80, newPercent));
	}

	function handleResizeEnd() {
		isResizing = false;
		document.removeEventListener('mousemove', handleResizeMove);
		document.removeEventListener('mouseup', handleResizeEnd);
	}
</script>

<svelte:window onkeydown={handleKeydown} />

<div class="bg-gray-800 rounded-lg border border-gray-700 overflow-hidden">
	<!-- Header -->
	<div class="p-6 border-b border-gray-700 bg-gray-800">
		<div class="flex items-start justify-between mb-4">
			<div>
				<h1 class="text-2xl font-bold text-gray-100">{agent.frontmatter.name}</h1>
				<p class="text-gray-400 mt-1">{agent.frontmatter.description}</p>
			</div>
			<div class="flex flex-col items-end gap-2">
				<div class="flex items-center gap-2">
					<span class="text-sm px-3 py-1 rounded border {getTierColor(agent.frontmatter.tier)}">
						{agent.frontmatter.tier}
					</span>
					<span class="text-sm px-3 py-1 rounded {getModelColor(agent.frontmatter.model)}">
						{agent.frontmatter.model}
					</span>
				</div>
				{#if agent.frontmatter.model_fallbacks && agent.frontmatter.model_fallbacks.length > 0}
					<div class="flex items-center gap-1.5 text-xs text-gray-500">
						<span class="text-gray-600">fallbacks:</span>
						{#each agent.frontmatter.model_fallbacks as fallback, i}
							<span class="px-1.5 py-0.5 bg-gray-700/50 rounded text-gray-400">{fallback}</span>
						{/each}
					</div>
				{/if}
			</div>
		</div>

		<div class="flex items-center gap-4 text-sm text-gray-400">
			<span class="flex items-center gap-1">
				<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
					<path
						stroke-linecap="round"
						stroke-linejoin="round"
						stroke-width="2"
						d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z"
					/>
				</svg>
				{agent.category} / {agent.subcategory}
			</span>
			{#if agent.frontmatter.role}
				<span class="flex items-center gap-1">
					<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path
							stroke-linecap="round"
							stroke-linejoin="round"
							stroke-width="2"
							d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z"
						/>
					</svg>
					{agent.frontmatter.role}
				</span>
			{/if}
			{#if agent.frontmatter.version}
				<span>v{agent.frontmatter.version}</span>
			{/if}
		</div>

		<div class="flex items-center gap-3 mt-4">
			<!-- Edit Toggle Button -->
			<button
				type="button"
				class="px-4 py-2 text-sm font-medium rounded-lg transition-all {isEditMode
					? 'bg-yellow-600 text-white hover:bg-yellow-700'
					: 'bg-blue-600 text-white hover:bg-blue-700'}"
				onclick={toggleEditMode}
			>
				{#if isEditMode}
					<span class="flex items-center gap-2">
						<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
						</svg>
						Exit Edit Mode
					</span>
				{:else}
					<span class="flex items-center gap-2">
						<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
						</svg>
						Edit Agent
					</span>
				{/if}
			</button>

			{#if isEditMode}
				<!-- Edit Mode Actions -->
				{#if isDirty}
					<span class="text-xs px-2 py-1 bg-yellow-900/50 text-yellow-300 rounded">Unsaved changes</span>
				{/if}

				<button
					type="button"
					class="px-3 py-2 text-sm text-gray-300 border border-gray-600 rounded-lg hover:bg-gray-700 transition-colors disabled:opacity-50"
					onclick={handleReset}
					disabled={!isDirty}
				>
					Reset
				</button>

				<button
					type="button"
					class="px-4 py-2 text-sm bg-green-600 text-white font-medium rounded-lg hover:bg-green-700 transition-colors disabled:opacity-50"
					onclick={handleSave}
					disabled={!isDirty || isSaving}
				>
					{isSaving ? 'Saving...' : 'Save'}
				</button>
			{:else}
				<button
					type="button"
					onclick={handleExport}
					class="px-4 py-2 border border-gray-600 text-gray-300 text-sm font-medium rounded-lg hover:bg-gray-700 transition-colors flex items-center gap-2"
				>
					<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
					</svg>
					Export
				</button>
				<a
					href="https://github.com/turbobeest/agents/blob/main/{agent.relativePath}"
					target="_blank"
					rel="noopener noreferrer"
					class="px-4 py-2 border border-gray-600 text-gray-300 text-sm font-medium rounded-lg hover:bg-gray-700 transition-colors"
				>
					View on GitHub
				</a>
			{/if}
		</div>

		{#if saveError}
			<div class="mt-3 px-3 py-2 bg-red-900/50 border border-red-700 text-red-300 text-sm rounded-lg">
				{saveError}
			</div>
		{/if}

		{#if saveSuccess}
			<div class="mt-3 px-3 py-2 bg-green-900/50 border border-green-700 text-green-300 text-sm rounded-lg flex items-center gap-2">
				<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
					<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
				</svg>
				Saved successfully
			</div>
		{/if}
	</div>

	{#if isEditMode}
		<!-- Edit Mode: Split Editor with Resizable Divider -->
		<div
			class="flex h-[600px] relative"
			class:cursor-col-resize={isResizing}
			class:select-none={isResizing}
			bind:this={containerRef}
		>
			<!-- Code Editor -->
			<div class="flex flex-col overflow-hidden" style="width: {splitPercent}%">
				<div class="px-4 py-2 bg-gray-850 border-b border-gray-700 text-xs text-gray-400 font-medium">
					Editor · {editContent.split('\n').length} lines
				</div>
				<textarea
					class="flex-1 w-full p-4 font-mono text-sm resize-none focus:outline-none bg-gray-900 text-gray-100"
					value={editContent}
					oninput={handleInput}
					spellcheck="false"
				></textarea>
			</div>

			<!-- Resizable Divider -->
			<div
				class="w-1 bg-gray-700 hover:bg-blue-500 cursor-col-resize transition-colors flex-shrink-0 relative group"
				onmousedown={handleResizeStart}
				role="separator"
				aria-orientation="vertical"
				tabindex="0"
			>
				<div class="absolute inset-y-0 -left-1 -right-1 group-hover:bg-blue-500/20"></div>
			</div>

			<!-- Live Preview -->
			<div class="flex flex-col overflow-hidden bg-gray-800" style="width: {100 - splitPercent}%">
				<div class="px-4 py-2 bg-gray-850 border-b border-gray-700 text-xs text-gray-400 font-medium">
					Preview
				</div>
				<div class="flex-1 overflow-y-auto">
					<div class="p-6 prose prose-sm prose-invert max-w-none">
						{@html renderEditPreview()}
					</div>
				</div>
			</div>
		</div>

		<!-- Status Bar -->
		<div class="px-4 py-2 border-t border-gray-700 bg-gray-800 text-xs text-gray-400 flex items-center justify-between">
			<span>{editContent.length} characters</span>
			<span>Drag divider to resize · Cmd/Ctrl+S to save · Esc to exit</span>
		</div>
	{:else}
		<!-- View Mode: Tabs -->
		<div class="border-b border-gray-700">
			<nav class="flex -mb-px">
				{#each tabs as tab}
					<button
						type="button"
						class="px-6 py-3 text-sm font-medium border-b-2 transition-colors
							{activeTab === tab.id
							? 'border-blue-500 text-blue-400'
							: 'border-transparent text-gray-400 hover:text-gray-300 hover:border-gray-600'}"
						onclick={() => (activeTab = tab.id)}
					>
						{tab.label}
					</button>
				{/each}
			</nav>
		</div>

		<!-- Tab Content -->
		<div class="p-6">
			{#if activeTab === 'overview'}
				<div class="space-y-6">
					<!-- Identity -->
					{#if agent.content.identity}
						<section>
							<h2 class="text-lg font-semibold text-gray-100 mb-3">Identity</h2>
							<div class="prose prose-sm prose-invert max-w-none">
								{@html renderMarkdown(agent.content.identity)}
							</div>
						</section>
					{/if}

					<!-- Vocabulary -->
					{#if agent.content.vocabulary && agent.content.vocabulary.length > 0}
						<section>
							<h2 class="text-lg font-semibold text-gray-100 mb-3">Vocabulary</h2>
							<div class="flex flex-wrap gap-2">
								{#each agent.content.vocabulary as term}
									<span class="px-3 py-1 bg-gray-700 text-gray-300 rounded-full text-sm">{term}</span>
								{/each}
							</div>
						</section>
					{/if}

					<!-- Never -->
					{#if agent.content.never && agent.content.never.length > 0}
						<section>
							<h2 class="text-lg font-semibold text-gray-100 mb-3">Never</h2>
							<ul class="space-y-2">
								{#each agent.content.never as item}
									<li class="flex items-start gap-2 text-sm text-red-300 bg-red-900/30 p-3 rounded border border-red-800">
										<svg class="w-5 h-5 flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
											<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M18.364 18.364A9 9 0 005.636 5.636m12.728 12.728A9 9 0 015.636 5.636m12.728 12.728L5.636 5.636" />
										</svg>
										{item}
									</li>
								{/each}
							</ul>
						</section>
					{/if}
				</div>

			{:else if activeTab === 'instructions'}
				<div class="space-y-6">
					{#if agent.content.instructions}
						{#if agent.content.instructions.always}
							<section>
								<h2 class="text-lg font-semibold text-gray-100 mb-3">Always</h2>
								<ol class="list-decimal list-inside space-y-2">
									{#each agent.content.instructions.always as item}
										<li class="text-sm text-gray-300">{item}</li>
									{/each}
								</ol>
							</section>
						{/if}

						{#if agent.content.instructions.generative}
							<section>
								<h2 class="text-lg font-semibold text-gray-100 mb-3">When Generative</h2>
								<ol class="list-decimal list-inside space-y-2">
									{#each agent.content.instructions.generative as item}
										<li class="text-sm text-gray-300">{item}</li>
									{/each}
								</ol>
							</section>
						{/if}

						{#if agent.content.instructions.critical}
							<section>
								<h2 class="text-lg font-semibold text-gray-100 mb-3">When Critical</h2>
								<ol class="list-decimal list-inside space-y-2">
									{#each agent.content.instructions.critical as item}
										<li class="text-sm text-gray-300">{item}</li>
									{/each}
								</ol>
							</section>
						{/if}

						{#if agent.content.instructions.evaluative}
							<section>
								<h2 class="text-lg font-semibold text-gray-100 mb-3">When Evaluative</h2>
								<ol class="list-decimal list-inside space-y-2">
									{#each agent.content.instructions.evaluative as item}
										<li class="text-sm text-gray-300">{item}</li>
									{/each}
								</ol>
							</section>
						{/if}

						{#if agent.content.instructions.informative}
							<section>
								<h2 class="text-lg font-semibold text-gray-100 mb-3">When Informative</h2>
								<ol class="list-decimal list-inside space-y-2">
									{#each agent.content.instructions.informative as item}
										<li class="text-sm text-gray-300">{item}</li>
									{/each}
								</ol>
							</section>
						{/if}
					{/if}
				</div>

			{:else if activeTab === 'specializations'}
				<div class="space-y-6">
					{#if agent.content.specializations}
						{#each Object.entries(agent.content.specializations) as [name, content]}
							<section>
								<h2 class="text-lg font-semibold text-gray-100 mb-3">{name}</h2>
								<div class="prose prose-sm prose-invert max-w-none bg-gray-700/50 p-4 rounded-lg">
									{@html renderMarkdown(content)}
								</div>
							</section>
						{/each}
					{:else}
						<p class="text-gray-400">No specializations defined.</p>
					{/if}
				</div>

			{:else if activeTab === 'config'}
				<div class="space-y-6">
					<!-- Tools -->
					{#if agent.frontmatter.tools}
						<section>
							<h2 class="text-lg font-semibold text-gray-100 mb-3">Tools</h2>
							<div class="grid gap-3">
								{#each Object.entries(agent.frontmatter.tools) as [mode, tools]}
									<div class="flex items-center gap-4 p-3 bg-gray-700/50 rounded">
										<span class="font-medium text-sm w-24 capitalize text-gray-200">{mode}:</span>
										<span class="text-sm text-gray-400">{tools}</span>
									</div>
								{/each}
							</div>
						</section>
					{/if}

					<!-- Cognitive Modes -->
					{#if agent.frontmatter.cognitive_modes}
						<section>
							<h2 class="text-lg font-semibold text-gray-100 mb-3">Cognitive Modes</h2>
							<div class="space-y-3">
								{#each Object.entries(agent.frontmatter.cognitive_modes).filter(([k]) => k !== 'default') as [mode, config]}
									{#if typeof config === 'object' && config !== null}
										<div class="p-3 bg-gray-700/50 rounded">
											<h3 class="font-medium text-sm capitalize mb-2 text-gray-200">{mode}</h3>
											<p class="text-sm text-gray-400"><strong class="text-gray-300">Mindset:</strong> {config.mindset}</p>
											<p class="text-sm text-gray-400"><strong class="text-gray-300">Output:</strong> {config.output}</p>
										</div>
									{/if}
								{/each}
								<p class="text-sm text-gray-400">Default: {agent.frontmatter.cognitive_modes.default}</p>
							</div>
						</section>
					{/if}

					<!-- Escalation -->
					{#if agent.frontmatter.escalation}
						<section>
							<h2 class="text-lg font-semibold text-gray-100 mb-3">Escalation</h2>
							<div class="p-3 bg-gray-700/50 rounded space-y-2">
								<p class="text-sm text-gray-300"><strong>Threshold:</strong> {agent.frontmatter.escalation.confidence_threshold}</p>
								<p class="text-sm text-gray-300"><strong>Escalate to:</strong> {agent.frontmatter.escalation.escalate_to}</p>
								<div>
									<strong class="text-sm text-gray-300">Triggers:</strong>
									<ul class="list-disc list-inside mt-1">
										{#each agent.frontmatter.escalation.triggers as trigger}
											<li class="text-sm text-gray-400">{trigger}</li>
										{/each}
									</ul>
								</div>
							</div>
						</section>
					{/if}

					<!-- Knowledge Sources -->
					{#if agent.content.knowledgeSources && agent.content.knowledgeSources.length > 0}
						<section>
							<h2 class="text-lg font-semibold text-gray-100 mb-3">Knowledge Sources</h2>
							<ul class="space-y-2">
								{#each agent.content.knowledgeSources as url}
									<li>
										<a href={url} target="_blank" rel="noopener noreferrer" class="text-sm text-blue-400 hover:underline">
											{url}
										</a>
									</li>
								{/each}
							</ul>
						</section>
					{/if}
				</div>

			{:else if activeTab === 'raw'}
				<div>
					<pre class="bg-gray-900 text-gray-100 p-4 rounded-lg overflow-x-auto text-sm">{agent.rawContent}</pre>
				</div>
			{/if}
		</div>
	{/if}
</div>
