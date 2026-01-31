<script lang="ts">
  import '../app.css';
  import Sidebar from '$lib/components/Sidebar.svelte';
  import Header from '$lib/components/Header.svelte';
  import { sidebarOpen } from '$lib/stores';

  let { children, data } = $props();
</script>

<div class="min-h-screen flex flex-col bg-slate-900">
  <Header stats={data.stats} />

  <div class="flex flex-1">
    {#if $sidebarOpen}
      <Sidebar navigation={data.navigation} />
    {/if}

    <main class="flex-1 p-6 overflow-auto">
      {@render children()}
    </main>
  </div>
</div>
