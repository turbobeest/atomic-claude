<script lang="ts">
	import '../app.css';
	import Header from '$lib/components/layout/Header.svelte';
	import Sidebar from '$lib/components/layout/Sidebar.svelte';
	import { navigation, syncStatus, user, errorMessage, clearError } from '$lib/stores';
	import { onMount } from 'svelte';
	import { base } from '$app/paths';

	let { children, data } = $props();

	// Initialize stores from server data
	$effect(() => {
		if (data.navigation) {
			navigation.set(data.navigation);
		}
		if (data.syncStatus) {
			syncStatus.set(data.syncStatus);
		}
		if (data.user) {
			user.set(data.user);
		}
	});

	// Periodic sync status check (only in local mode)
	onMount(() => {
		if (base) return; // Skip in static mode (base path is set)

		const interval = setInterval(async () => {
			try {
				const response = await fetch(`${base}/api/sync`);
				const result = await response.json();
				if (result.success) {
					syncStatus.set(result.data);
				}
			} catch {
				// Silent fail
			}
		}, 60000); // Check every minute

		return () => clearInterval(interval);
	});
</script>

<svelte:head>
	<title>Agent Manager</title>
	<meta name="description" content="Manage PhD-grade agent definitions" />
</svelte:head>

<div class="min-h-screen bg-gray-900 flex flex-col">
	<Header />

	<div class="flex flex-1 overflow-hidden">
		<Sidebar categories={$navigation} />

		<main class="flex-1 overflow-y-auto p-6">
			{#if $errorMessage}
				<div class="mb-4 p-4 bg-red-900/50 border border-red-700 rounded-lg flex items-center justify-between">
					<span class="text-red-300">{$errorMessage}</span>
					<button type="button" class="text-red-400 hover:text-red-300" onclick={() => clearError()} aria-label="Close">
						<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
						</svg>
					</button>
				</div>
			{/if}

			{@render children()}
		</main>
	</div>
</div>
