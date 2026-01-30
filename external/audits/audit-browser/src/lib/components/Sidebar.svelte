<script lang="ts">
  import { onMount } from 'svelte';
  import type { NavCategory } from '$lib/types';
  import { toggleCategory, toggleSubcategory, expandedCategories, expandedSubcategories, setFilter } from '$lib/stores';
  import { CATEGORY_CLUSTERS } from '$lib/types';

  interface Props {
    navigation: NavCategory[];
  }

  let { navigation }: Props = $props();

  // Resizable sidebar state
  const MIN_WIDTH = 200;
  const MAX_WIDTH = 600;
  const DEFAULT_WIDTH = 320;

  let sidebarWidth = $state(DEFAULT_WIDTH);
  let isResizing = $state(false);

  onMount(() => {
    // Load saved width from localStorage
    const saved = localStorage.getItem('sidebar-width');
    if (saved) {
      const width = parseInt(saved, 10);
      if (width >= MIN_WIDTH && width <= MAX_WIDTH) {
        sidebarWidth = width;
      }
    }
  });

  function startResize(e: MouseEvent) {
    isResizing = true;
    e.preventDefault();

    const startX = e.clientX;
    const startWidth = sidebarWidth;

    function onMouseMove(e: MouseEvent) {
      const delta = e.clientX - startX;
      const newWidth = Math.min(MAX_WIDTH, Math.max(MIN_WIDTH, startWidth + delta));
      sidebarWidth = newWidth;
    }

    function onMouseUp() {
      isResizing = false;
      localStorage.setItem('sidebar-width', sidebarWidth.toString());
      document.removeEventListener('mousemove', onMouseMove);
      document.removeEventListener('mouseup', onMouseUp);
      document.body.style.cursor = '';
      document.body.style.userSelect = '';
    }

    document.addEventListener('mousemove', onMouseMove);
    document.addEventListener('mouseup', onMouseUp);
    document.body.style.cursor = 'col-resize';
    document.body.style.userSelect = 'none';
  }

  function getCategoryCluster(categoryNumber: number): string {
    for (const [name, config] of Object.entries(CATEGORY_CLUSTERS)) {
      if (categoryNumber >= config.range[0] && categoryNumber <= config.range[1]) {
        return name;
      }
    }
    return 'Core Technical';
  }

  function getClusterColor(cluster: string): string {
    const colors: Record<string, string> = {
      'Core Technical': 'border-l-blue-500',
      'Infrastructure': 'border-l-green-500',
      'Human & Experience': 'border-l-purple-500',
      'Process & Governance': 'border-l-orange-500',
      'Economics & Dependencies': 'border-l-yellow-500',
      'Specialized Domains': 'border-l-red-500'
    };
    return colors[cluster] || 'border-l-gray-500';
  }

  function getStatusColor(status: string): string {
    return status === 'active' ? 'bg-emerald-500' : 'bg-amber-500';
  }
</script>

<aside
  class="bg-slate-800 border-r border-slate-700 overflow-y-auto h-[calc(100vh-73px)] sticky top-[73px] relative flex-shrink-0"
  style="width: {sidebarWidth}px"
>
  <!-- Resize handle -->
  <div
    class="absolute top-0 right-0 w-1 h-full cursor-col-resize hover:bg-blue-400 transition-colors z-10 {isResizing ? 'bg-blue-500' : 'bg-transparent hover:bg-blue-300'}"
    onmousedown={startResize}
    role="separator"
    aria-orientation="vertical"
    aria-label="Resize sidebar"
    tabindex="0"
  ></div>

  <div class="p-4">
    <h2 class="text-sm font-semibold text-slate-400 uppercase tracking-wider mb-3">Categories</h2>

    <nav class="space-y-1">
      {#each navigation as category}
        {@const cluster = getCategoryCluster(category.number)}
        {@const clusterColor = getClusterColor(cluster)}

        <div class="border-l-4 {clusterColor}">
          <button
            onclick={() => toggleCategory(category.id)}
            class="w-full flex items-center justify-between px-3 py-2 text-left hover:bg-slate-700 transition-colors"
          >
            <div class="flex items-center gap-2 min-w-0">
              <span class="text-xs font-mono text-slate-500">{category.number}.</span>
              <span class="font-medium text-slate-200 truncate">{category.title}</span>
            </div>
            <div class="flex items-center gap-2 shrink-0">
              <span class="text-xs text-slate-400 bg-slate-700 px-1.5 py-0.5 rounded">{category.auditCount}</span>
              <svg
                class="w-4 h-4 text-slate-500 transition-transform {$expandedCategories.has(category.id) ? 'rotate-90' : ''}"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7" />
              </svg>
            </div>
          </button>

          {#if $expandedCategories.has(category.id)}
            <div class="ml-4 border-l border-slate-600">
              {#each category.subcategories as subcategory}
                <div>
                  <button
                    onclick={() => toggleSubcategory(subcategory.id)}
                    class="w-full flex items-center justify-between px-3 py-1.5 text-left text-sm hover:bg-slate-700 transition-colors"
                  >
                    <span class="text-slate-300 truncate">{subcategory.title}</span>
                    <div class="flex items-center gap-2 shrink-0">
                      <span class="text-xs text-slate-500">{subcategory.audits.length}</span>
                      <svg
                        class="w-3 h-3 text-slate-500 transition-transform {$expandedSubcategories.has(subcategory.id) ? 'rotate-90' : ''}"
                        fill="none"
                        stroke="currentColor"
                        viewBox="0 0 24 24"
                      >
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7" />
                      </svg>
                    </div>
                  </button>

                  {#if $expandedSubcategories.has(subcategory.id)}
                    <div class="ml-3 py-1">
                      {#each subcategory.audits as audit}
                        <button
                          onclick={() => setFilter('category', category.slug)}
                          class="w-full flex items-center gap-2 px-3 py-1 text-left text-xs hover:bg-slate-700 transition-colors group"
                        >
                          <span class="w-1.5 h-1.5 rounded-full {getStatusColor(audit.status)}"></span>
                          <span class="text-slate-400 truncate group-hover:text-slate-200">{audit.name}</span>
                          {#if audit.status === 'planned'}
                            <span class="text-[10px] text-amber-400 bg-amber-900/50 px-1 rounded">planned</span>
                          {/if}
                        </button>
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

  <!-- Legend -->
  <div class="p-4 border-t border-slate-700 mt-4">
    <h3 class="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">Legend</h3>
    <div class="space-y-2 text-xs">
      <div class="flex items-center gap-2">
        <span class="w-2 h-2 rounded-full bg-emerald-500"></span>
        <span class="text-slate-400">Active</span>
      </div>
      <div class="flex items-center gap-2">
        <span class="w-2 h-2 rounded-full bg-amber-500"></span>
        <span class="text-slate-400">Planned</span>
      </div>
    </div>
    <h3 class="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2 mt-4">Audit Type</h3>
    <div class="space-y-2 text-xs">
      <div class="flex items-center gap-2">
        <span class="w-2 h-2 rounded-full bg-green-500"></span>
        <span class="text-slate-400">Deterministic</span>
      </div>
      <div class="flex items-center gap-2">
        <span class="w-2 h-2 rounded-full bg-amber-500"></span>
        <span class="text-slate-400">Non-deterministic</span>
      </div>
    </div>
  </div>
</aside>
