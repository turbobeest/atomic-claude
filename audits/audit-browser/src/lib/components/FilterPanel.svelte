<script lang="ts">
  import { filters, setFilter, removeFilter, hasActiveFilters, activeFiltersCount } from '$lib/stores';
  import { SDLC_PHASES } from '$lib/types';

  interface Props {
    filterOptions: {
      categories: string[];
      tiers: readonly string[];
      statuses: readonly string[];
      automationLevels: readonly string[];
    };
  }

  let { filterOptions }: Props = $props();
  let expanded = $state(true); // Start expanded by default

  function formatLabel(value: string): string {
    return value
      .split(/[-_]/)
      .map(word => word.charAt(0).toUpperCase() + word.slice(1))
      .join(' ');
  }

  // Toggle boolean filter
  function toggleBooleanFilter(key: string, currentValue: boolean | undefined) {
    if (currentValue === true) {
      removeFilter(key as any);
    } else {
      setFilter(key as any, true);
    }
  }
</script>

<div class="bg-slate-800 rounded-lg border border-slate-700 p-4">
  <button
    onclick={() => expanded = !expanded}
    class="w-full flex items-center justify-between cursor-pointer"
  >
    <div class="flex items-center gap-2 text-sm font-medium text-slate-200">
      <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 4a1 1 0 011-1h16a1 1 0 011 1v2.586a1 1 0 01-.293.707l-6.414 6.414a1 1 0 00-.293.707V17l-4 4v-6.586a1 1 0 00-.293-.707L3.293 7.293A1 1 0 013 6.586V4z" />
      </svg>
      Filters
      {#if $hasActiveFilters}
        <span class="bg-blue-900 text-blue-300 text-xs px-2 py-0.5 rounded-full">{$activeFiltersCount}</span>
      {/if}
    </div>

    <svg
      class="w-5 h-5 text-slate-500 transition-transform {expanded ? 'rotate-180' : ''}"
      fill="none"
      stroke="currentColor"
      viewBox="0 0 24 24"
    >
      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
    </svg>
  </button>

  {#if expanded}
    <div class="mt-4 space-y-5 animate-fade-in">

      <!-- Row 1: Status, Category, Automation -->
      <div class="flex flex-wrap gap-4">
        <!-- Status -->
        <div class="space-y-1">
          <label class="text-xs font-medium text-slate-400 uppercase">Status</label>
          <select
            value={$filters.status || ''}
            onchange={(e) => {
              const value = (e.target as HTMLSelectElement).value;
              if (value) setFilter('status', value as 'active' | 'planned');
              else removeFilter('status');
            }}
            class="block w-32 px-3 py-1.5 text-sm border border-slate-600 rounded-md bg-slate-700 text-slate-200 focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value="">All</option>
            <option value="active">Active</option>
            <option value="planned">Planned</option>
          </select>
        </div>

        <!-- Category -->
        <div class="space-y-1">
          <label class="text-xs font-medium text-slate-400 uppercase">Category</label>
          <select
            value={$filters.category || ''}
            onchange={(e) => {
              const value = (e.target as HTMLSelectElement).value;
              if (value) setFilter('category', value);
              else removeFilter('category');
            }}
            class="block w-52 px-3 py-1.5 text-sm border border-slate-600 rounded-md bg-slate-700 text-slate-200 focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value="">All Categories</option>
            {#each filterOptions.categories as category}
              <option value={category}>{formatLabel(category)}</option>
            {/each}
          </select>
        </div>
      </div>

      <!-- SDLC Phase -->
      <div class="space-y-2">
        <label class="text-xs font-medium text-slate-400 uppercase">When to Run (SDLC Phase)</label>
        <div class="flex flex-wrap gap-2">
          {#each SDLC_PHASES as phase}
            <button
              onclick={() => {
                if ($filters.sdlcPhase === phase.id) {
                  removeFilter('sdlcPhase');
                } else {
                  setFilter('sdlcPhase', phase.id);
                }
              }}
              class="px-3 py-1.5 text-xs rounded-full border transition-colors {$filters.sdlcPhase === phase.id
                ? 'bg-blue-500 text-white border-blue-500'
                : 'bg-slate-700 text-slate-300 border-slate-600 hover:border-blue-400'}"
              title={phase.description}
            >
              {phase.label}
            </button>
          {/each}
        </div>
      </div>

      <!-- Requirements -->
      <div class="space-y-2">
        <label class="text-xs font-medium text-slate-400 uppercase">Requirements (What the audit needs)</label>
        <div class="flex flex-wrap gap-2">
          <button
            onclick={() => toggleBooleanFilter('requiresSourceCode', $filters.requiresSourceCode)}
            class="px-3 py-1.5 text-xs rounded-full border transition-colors {$filters.requiresSourceCode
              ? 'bg-slate-500 text-white border-slate-500'
              : 'bg-slate-700 text-slate-300 border-slate-600 hover:border-slate-400'}"
          >
            Source Code
          </button>
          <button
            onclick={() => toggleBooleanFilter('requiresRuntimeData', $filters.requiresRuntimeData)}
            class="px-3 py-1.5 text-xs rounded-full border transition-colors {$filters.requiresRuntimeData
              ? 'bg-slate-500 text-white border-slate-500'
              : 'bg-slate-700 text-slate-300 border-slate-600 hover:border-slate-400'}"
          >
            Runtime Data
          </button>
          <button
            onclick={() => toggleBooleanFilter('requiresProductionAccess', $filters.requiresProductionAccess)}
            class="px-3 py-1.5 text-xs rounded-full border transition-colors {$filters.requiresProductionAccess
              ? 'bg-slate-500 text-white border-slate-500'
              : 'bg-slate-700 text-slate-300 border-slate-600 hover:border-slate-400'}"
          >
            Production Access
          </button>
          <button
            onclick={() => toggleBooleanFilter('requiresTeamInput', $filters.requiresTeamInput)}
            class="px-3 py-1.5 text-xs rounded-full border transition-colors {$filters.requiresTeamInput
              ? 'bg-slate-500 text-white border-slate-500'
              : 'bg-slate-700 text-slate-300 border-slate-600 hover:border-slate-400'}"
          >
            Team Input
          </button>
        </div>
        <p class="text-[10px] text-slate-500">Click to filter for audits that require these resources</p>
      </div>

      <!-- Special Requirements (from meta-audit) -->
      <div class="space-y-2">
        <label class="text-xs font-medium text-slate-400 uppercase">Special Requirements</label>
        <div class="flex flex-wrap gap-2">
          <button
            onclick={() => toggleBooleanFilter('requiresPhysicalAccess', $filters.requiresPhysicalAccess)}
            class="px-3 py-1.5 text-xs rounded-full border transition-colors {$filters.requiresPhysicalAccess
              ? 'bg-orange-500 text-white border-orange-500'
              : 'bg-slate-700 text-slate-300 border-slate-600 hover:border-orange-400'}"
            title="Requires physical access to hardware, sensors, or equipment"
          >
            Physical Access
          </button>
          <button
            onclick={() => toggleBooleanFilter('requiresHumanEvaluation', $filters.requiresHumanEvaluation)}
            class="px-3 py-1.5 text-xs rounded-full border transition-colors {$filters.requiresHumanEvaluation
              ? 'bg-purple-500 text-white border-purple-500'
              : 'bg-slate-700 text-slate-300 border-slate-600 hover:border-purple-400'}"
            title="Requires human perception testing or subjective evaluation"
          >
            Human Evaluation
          </button>
          <button
            onclick={() => toggleBooleanFilter('requiresInterviews', $filters.requiresInterviews)}
            class="px-3 py-1.5 text-xs rounded-full border transition-colors {$filters.requiresInterviews
              ? 'bg-cyan-500 text-white border-cyan-500'
              : 'bg-slate-700 text-slate-300 border-slate-600 hover:border-cyan-400'}"
            title="Requires stakeholder interviews or surveys"
          >
            Interviews
          </button>
        </div>
        <p class="text-[10px] text-slate-500">Audits with special requirements that may limit automation</p>
      </div>

    </div>
  {/if}
</div>
