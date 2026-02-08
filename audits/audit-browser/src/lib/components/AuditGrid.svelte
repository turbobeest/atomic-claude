<script lang="ts">
  import type { AuditInventoryRow } from '$lib/types';
  import AuditCard from './AuditCard.svelte';

  interface Props {
    audits: AuditInventoryRow[];
    onselect?: (audit: AuditInventoryRow) => void;
  }

  let { audits, onselect }: Props = $props();

  // Group audits by category for better organization
  let groupedAudits = $derived(() => {
    const groups = new Map<string, AuditInventoryRow[]>();
    for (const audit of audits) {
      const key = audit.category;
      if (!groups.has(key)) {
        groups.set(key, []);
      }
      groups.get(key)!.push(audit);
    }
    return groups;
  });

  let showGrouped = $state(false);
</script>

<div class="space-y-4">
  <div class="flex items-center justify-between">
    <span class="text-sm text-slate-400">{audits.length} audits</span>
    <button
      onclick={() => showGrouped = !showGrouped}
      class="text-sm text-blue-400 hover:text-blue-300"
    >
      {showGrouped ? 'Show flat list' : 'Group by category'}
    </button>
  </div>

  {#if showGrouped}
    <div class="space-y-6">
      {#each [...groupedAudits().entries()] as [category, categoryAudits]}
        <div>
          <h3 class="text-lg font-semibold text-slate-100 mb-3 capitalize">
            {category.replace(/-/g, ' ')}
            <span class="text-sm font-normal text-slate-400">({categoryAudits.length})</span>
          </h3>
          <div class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
            {#each categoryAudits as audit (audit.audit_id)}
              <AuditCard {audit} onclick={() => onselect?.(audit)} />
            {/each}
          </div>
        </div>
      {/each}
    </div>
  {:else}
    <div class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
      {#each audits as audit (audit.audit_id)}
        <AuditCard {audit} onclick={() => onselect?.(audit)} />
      {/each}
    </div>
  {/if}

  {#if audits.length === 0}
    <div class="text-center py-12">
      <svg class="mx-auto h-12 w-12 text-slate-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9.172 16.172a4 4 0 015.656 0M9 10h.01M15 10h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
      </svg>
      <h3 class="mt-2 text-sm font-medium text-slate-200">No audits found</h3>
      <p class="mt-1 text-sm text-slate-400">Try adjusting your search or filters.</p>
    </div>
  {/if}
</div>
