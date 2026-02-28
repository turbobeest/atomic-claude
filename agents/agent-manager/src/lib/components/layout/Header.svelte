<script lang="ts">
	import { syncStatus, syncStatusText, user, searchQuery, sidebarCollapsed, toggleSidebar } from '$lib/stores';
	import { goto } from '$app/navigation';
	import { base } from '$app/paths';

	let searchInput = $state('');

	function handleSearch(e: Event) {
		e.preventDefault();
		if (searchInput.trim()) {
			searchQuery.set(searchInput.trim());
			goto(`${base}/search?q=${encodeURIComponent(searchInput.trim())}`);
		}
	}

	function getSyncStatusColor(status: string): string {
		switch (status) {
			case 'synced':
				return 'text-green-400';
			case 'local-changes':
				return 'text-yellow-400';
			case 'remote-changes':
				return 'text-blue-400';
			case 'conflict':
				return 'text-red-400';
			default:
				return 'text-gray-500';
		}
	}

	async function handleSync() {
		const response = await fetch('/api/sync', { method: 'POST' });
		const result = await response.json();
		if (result.success) {
			// Refresh status
			const statusResponse = await fetch('/api/sync');
			const statusResult = await statusResponse.json();
			if (statusResult.success) {
				syncStatus.set(statusResult.data);
			}
		}
	}
</script>

<header class="bg-gray-800 border-b border-gray-700 px-4 py-3 flex items-center justify-between">
	<div class="flex items-center gap-4">
		<!-- Hamburger Menu Button -->
		<button
			type="button"
			onclick={toggleSidebar}
			class="p-2 text-gray-400 hover:text-gray-200 hover:bg-gray-700 rounded-lg transition-colors"
			aria-label={$sidebarCollapsed ? 'Expand sidebar' : 'Collapse sidebar'}
		>
			{#if $sidebarCollapsed}
				<!-- Menu icon (3 lines) -->
				<svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
					<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 12h16M4 18h16" />
				</svg>
			{:else}
				<!-- Close/collapse icon -->
				<svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
					<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11 19l-7-7 7-7m8 14l-7-7 7-7" />
				</svg>
			{/if}
		</button>

		<a href="{base}/" class="flex items-center gap-2">
			<svg class="w-8 h-8 text-blue-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
				<path
					stroke-linecap="round"
					stroke-linejoin="round"
					stroke-width="2"
					d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10"
				/>
			</svg>
			<span class="text-xl font-semibold text-gray-100">Agent Manager</span>
		</a>

		<form onsubmit={handleSearch} class="relative ml-8">
			<input
				type="text"
				bind:value={searchInput}
				placeholder="Search agents..."
				class="w-80 pl-10 pr-4 py-2 bg-gray-700 border border-gray-600 rounded-lg text-sm text-gray-100 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
			/>
			<svg
				class="w-5 h-5 text-gray-400 absolute left-3 top-1/2 -translate-y-1/2"
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
		</form>
	</div>

	<div class="flex items-center gap-4">
		<!-- Sync Status -->
		<div class="flex items-center gap-2">
			<button
				type="button"
				class="flex items-center gap-2 px-3 py-1.5 text-sm rounded-md hover:bg-gray-700 transition-colors {getSyncStatusColor(
					$syncStatus.status
				)}"
				onclick={handleSync}
				title="Click to sync"
			>
				<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
					<path
						stroke-linecap="round"
						stroke-linejoin="round"
						stroke-width="2"
						d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
					/>
				</svg>
				<span>{$syncStatusText}</span>
			</button>
			<span class="text-xs text-gray-500">
				{$syncStatus.currentBranch}
			</span>
		</div>

		<!-- Create Button -->
		<a
			href="{base}/create"
			class="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 transition-colors"
		>
			<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
				<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4" />
			</svg>
			Create
		</a>

		<!-- User Menu -->
		{#if $user}
			<div class="flex items-center gap-2">
				<img src={$user.avatar_url} alt={$user.login} class="w-8 h-8 rounded-full" />
				<span class="text-sm text-gray-300">{$user.login}</span>
				<a href="{base}/auth/logout" class="text-sm text-gray-400 hover:text-gray-300">Logout</a>
			</div>
		{:else}
			<a
				href="{base}/auth/login"
				class="flex items-center gap-2 px-4 py-2 border border-gray-600 text-gray-300 text-sm font-medium rounded-lg hover:bg-gray-700 transition-colors"
			>
				<svg class="w-4 h-4" viewBox="0 0 24 24" fill="currentColor">
					<path
						d="M12 0c-6.626 0-12 5.373-12 12 0 5.302 3.438 9.8 8.207 11.387.599.111.793-.261.793-.577v-2.234c-3.338.726-4.033-1.416-4.033-1.416-.546-1.387-1.333-1.756-1.333-1.756-1.089-.745.083-.729.083-.729 1.205.084 1.839 1.237 1.839 1.237 1.07 1.834 2.807 1.304 3.492.997.107-.775.418-1.305.762-1.604-2.665-.305-5.467-1.334-5.467-5.931 0-1.311.469-2.381 1.236-3.221-.124-.303-.535-1.524.117-3.176 0 0 1.008-.322 3.301 1.23.957-.266 1.983-.399 3.003-.404 1.02.005 2.047.138 3.006.404 2.291-1.552 3.297-1.23 3.297-1.23.653 1.653.242 2.874.118 3.176.77.84 1.235 1.911 1.235 3.221 0 4.609-2.807 5.624-5.479 5.921.43.372.823 1.102.823 2.222v3.293c0 .319.192.694.801.576 4.765-1.589 8.199-6.086 8.199-11.386 0-6.627-5.373-12-12-12z"
					/>
				</svg>
				Sign in
			</a>
		{/if}
	</div>
</header>
