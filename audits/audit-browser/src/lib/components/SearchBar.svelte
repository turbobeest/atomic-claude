<script lang="ts">
  import { searchQuery } from '$lib/stores';

  let inputValue = $state($searchQuery);

  function handleInput(event: Event) {
    const target = event.target as HTMLInputElement;
    inputValue = target.value;
    searchQuery.set(target.value);
  }

  function handleClear() {
    inputValue = '';
    searchQuery.set('');
  }
</script>

<div class="relative w-full max-w-md">
  <div class="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
    <svg class="h-5 w-5 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
    </svg>
  </div>

  <input
    type="text"
    value={inputValue}
    oninput={handleInput}
    placeholder="Search audits by name, category, or ID..."
    class="block w-full pl-10 pr-10 py-2.5 border border-slate-600 rounded-lg bg-slate-800 text-sm text-slate-200 placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-shadow"
  />

  {#if inputValue}
    <button
      onclick={handleClear}
      class="absolute inset-y-0 right-0 pr-3 flex items-center"
      aria-label="Clear search"
    >
      <svg class="h-5 w-5 text-slate-400 hover:text-slate-300" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
      </svg>
    </button>
  {/if}
</div>
