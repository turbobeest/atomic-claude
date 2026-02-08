<script lang="ts">
	import type { Agent } from '$lib/types';
	import { marked } from 'marked';
	import { saveDraftToStorage, loadDraftFromStorage, clearDraftFromStorage } from '$lib/stores';

	interface Props {
		agent: Agent;
		onSave: (content: string) => Promise<void>;
		onCreateIssue?: ((content: string) => Promise<void>) | null;
		onCopyGhCommand?: ((content: string) => void) | null;
		staticMode?: boolean;
	}

	let {
		agent,
		onSave,
		onCreateIssue = null,
		onCopyGhCommand = null,
		staticMode = false
	}: Props = $props();

	let content = $state(agent.rawContent);
	let isDirty = $state(false);
	let isSaving = $state(false);
	let saveError = $state<string | null>(null);
	let showPreview = $state(true);
	let copiedCommand = $state(false);

	// Resizable panel state
	let splitPercent = $state(65);
	let isResizing = $state(false);
	let containerRef = $state<HTMLDivElement | null>(null);

	// Check for saved draft on mount
	$effect(() => {
		const draft = loadDraftFromStorage(agent.id);
		if (draft && draft !== agent.rawContent) {
			const useDraft = confirm('A draft was found for this agent. Do you want to restore it?');
			if (useDraft) {
				content = draft;
				isDirty = true;
			}
		}
	});

	// Auto-save draft
	$effect(() => {
		if (isDirty) {
			saveDraftToStorage(agent.id, content);
		}
	});

	function handleInput(e: Event) {
		const target = e.target as HTMLTextAreaElement;
		content = target.value;
		isDirty = content !== agent.rawContent;
	}

	async function handleSave() {
		if (!isDirty) return;

		isSaving = true;
		saveError = null;

		try {
			await onSave(content);
			if (!staticMode) {
				// Only mark as saved in local mode
				isDirty = false;
				clearDraftFromStorage(agent.id);
			}
		} catch (error) {
			saveError = error instanceof Error ? error.message : 'Failed to save';
		} finally {
			isSaving = false;
		}
	}

	function handleReset() {
		if (isDirty) {
			const confirmed = confirm('Are you sure you want to discard your changes?');
			if (!confirmed) return;
		}
		content = agent.rawContent;
		isDirty = false;
		clearDraftFromStorage(agent.id);
	}

	function handleCopyGhCommand() {
		if (onCopyGhCommand) {
			onCopyGhCommand(content);
			copiedCommand = true;
			setTimeout(() => (copiedCommand = false), 2000);
		}
	}

	function renderPreview(): string {
		// Extract markdown content (after frontmatter)
		const parts = content.split('---');
		if (parts.length >= 3) {
			const markdown = parts.slice(2).join('---');
			return marked(markdown) as string;
		}
		return marked(content) as string;
	}

	// Keyboard shortcuts
	function handleKeydown(e: KeyboardEvent) {
		if ((e.metaKey || e.ctrlKey) && e.key === 's') {
			e.preventDefault();
			handleSave();
		}
	}

	// Save button text based on mode
	const saveButtonText = $derived(() => {
		if (isSaving) return staticMode ? 'Opening...' : 'Saving...';
		if (staticMode) return 'Submit as Issue';
		return 'Save';
	});

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

<div class="h-full flex flex-col">
	<!-- Toolbar -->
	<div class="flex items-center justify-between p-3 border-b border-gray-700 bg-gray-800">
		<div class="flex items-center gap-3">
			<h2 class="font-semibold text-gray-100">Edit: {agent.frontmatter.name}</h2>
			{#if isDirty}
				<span class="text-xs px-2 py-1 bg-yellow-900/50 text-yellow-300 rounded">Unsaved changes</span>
			{/if}
			{#if staticMode}
				<span class="text-xs px-2 py-1 bg-purple-900/50 text-purple-300 rounded">Static Mode</span>
			{/if}
		</div>

		<div class="flex items-center gap-2">
			<button
				type="button"
				class="px-3 py-1.5 text-sm {showPreview ? 'bg-gray-600' : 'bg-gray-700'} text-gray-200 border border-gray-600 rounded hover:bg-gray-600 transition-colors"
				onclick={() => (showPreview = !showPreview)}
			>
				{showPreview ? 'Hide Preview' : 'Show Preview'}
			</button>

			<button
				type="button"
				class="px-3 py-1.5 text-sm text-gray-300 border border-gray-600 rounded hover:bg-gray-700 transition-colors disabled:opacity-50"
				onclick={handleReset}
				disabled={!isDirty}
			>
				Reset
			</button>

			<!-- Copy gh command button (for Claude Code users) -->
			{#if onCopyGhCommand}
				<button
					type="button"
					class="px-3 py-1.5 text-sm text-gray-300 border border-gray-600 rounded hover:bg-gray-700 transition-colors disabled:opacity-50 flex items-center gap-1.5"
					onclick={handleCopyGhCommand}
					disabled={!isDirty}
					title="Copy gh CLI command for Claude Code"
				>
					{#if copiedCommand}
						<svg class="w-4 h-4 text-green-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
						</svg>
						Copied!
					{:else}
						<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
						</svg>
						Copy gh command
					{/if}
				</button>
			{/if}

			<!-- In local mode, show separate Create Issue button -->
			{#if !staticMode && onCreateIssue}
				<button
					type="button"
					class="px-3 py-1.5 text-sm text-gray-300 border border-gray-600 rounded hover:bg-gray-700 transition-colors disabled:opacity-50"
					onclick={() => onCreateIssue?.(content)}
					disabled={!isDirty}
				>
					Create Issue
				</button>
			{/if}

			<!-- Main save/submit button -->
			<button
				type="button"
				class="px-4 py-1.5 text-sm {staticMode ? 'bg-purple-600 hover:bg-purple-700' : 'bg-blue-600 hover:bg-blue-700'} text-white rounded transition-colors disabled:opacity-50"
				onclick={handleSave}
				disabled={!isDirty || isSaving}
			>
				{saveButtonText()}
			</button>
		</div>
	</div>

	{#if saveError}
		<div class="px-3 py-2 bg-red-900/50 border-b border-red-700 text-red-300 text-sm">
			{saveError}
		</div>
	{/if}

	<!-- Editor Area -->
	<div
		class="flex-1 flex overflow-hidden relative"
		class:cursor-col-resize={isResizing}
		class:select-none={isResizing}
		bind:this={containerRef}
	>
		<!-- Code Editor -->
		<div
			class="flex flex-col overflow-hidden"
			style={showPreview ? `width: ${splitPercent}%` : 'width: 100%'}
		>
			<div class="px-4 py-2 text-xs text-gray-400 bg-gray-850 border-b border-gray-700 font-medium">
				Editor
			</div>
			<textarea
				class="flex-1 w-full p-4 font-mono text-sm resize-none focus:outline-none bg-gray-900 text-gray-100"
				value={content}
				oninput={handleInput}
				spellcheck="false"
			></textarea>
		</div>

		<!-- Resizable Divider -->
		{#if showPreview}
			<div
				class="w-1 bg-gray-700 hover:bg-blue-500 cursor-col-resize transition-colors flex-shrink-0 relative group"
				onmousedown={handleResizeStart}
				role="separator"
				aria-orientation="vertical"
				tabindex="0"
			>
				<div class="absolute inset-y-0 -left-1 -right-1 group-hover:bg-blue-500/20"></div>
			</div>
		{/if}

		<!-- Preview -->
		{#if showPreview}
			<div
				class="flex flex-col overflow-hidden bg-gray-800"
				style="width: {100 - splitPercent}%"
			>
				<div class="px-4 py-2 text-xs text-gray-400 bg-gray-850 border-b border-gray-700 font-medium">
					Preview
				</div>
				<div class="flex-1 overflow-y-auto">
					<div class="p-6 prose prose-sm prose-invert max-w-none">
						{@html renderPreview()}
					</div>
				</div>
			</div>
		{/if}
	</div>

	<!-- Status Bar -->
	<div class="px-3 py-2 border-t border-gray-700 bg-gray-800 text-xs text-gray-400 flex items-center justify-between">
		<span>
			{content.split('\n').length} lines | {content.length} characters
		</span>
		<span>
			{#if staticMode}
				Changes will be submitted as GitHub Issue
			{:else}
				Press Cmd/Ctrl+S to save
			{/if}
		</span>
	</div>
</div>
