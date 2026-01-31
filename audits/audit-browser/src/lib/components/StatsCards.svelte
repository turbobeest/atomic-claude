<script lang="ts">
  interface Props {
    stats: {
      total: number;
      active: number;
      planned: number;
      byTier: {
        focused: number;
        expert: number;
        phd: number;
        standard: number;
      };
      byAutomation: {
        fullyAutomated: number;
        semiAutomated: number;
        humanRequired: number;
      };
      categories: number;
    };
  }

  let { stats }: Props = $props();

  // Calculate derived stats
  let deterministic = $derived(() => stats.byAutomation.fullyAutomated);
  let nonDeterministic = $derived(() => stats.byAutomation.semiAutomated + stats.byAutomation.humanRequired);
  let activePercent = $derived(() => Math.round((stats.active / stats.total) * 100));
</script>

<div class="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
  <!-- Total -->
  <div class="bg-slate-800 rounded-lg border border-slate-700 p-4">
    <div class="text-2xl font-bold text-slate-100">{stats.total.toLocaleString()}</div>
    <div class="text-sm text-slate-400">Total Audits</div>
  </div>

  <!-- Active -->
  <div class="bg-slate-800 rounded-lg border border-slate-700 p-4">
    <div class="text-2xl font-bold text-emerald-400">{stats.active.toLocaleString()}</div>
    <div class="text-sm text-slate-400">Active ({activePercent()}%)</div>
  </div>

  <!-- Planned -->
  <div class="bg-slate-800 rounded-lg border border-slate-700 p-4">
    <div class="text-2xl font-bold text-amber-400">{stats.planned.toLocaleString()}</div>
    <div class="text-sm text-slate-400">Planned</div>
  </div>

  <!-- Categories -->
  <div class="bg-slate-800 rounded-lg border border-slate-700 p-4">
    <div class="text-2xl font-bold text-blue-400">{stats.categories}</div>
    <div class="text-sm text-slate-400">Categories</div>
  </div>

  <!-- Deterministic -->
  <div class="bg-slate-800 rounded-lg border border-slate-700 p-4">
    <div class="text-2xl font-bold text-green-400">{deterministic().toLocaleString()}</div>
    <div class="text-sm text-slate-400">Deterministic</div>
  </div>

  <!-- Non-deterministic -->
  <div class="bg-slate-800 rounded-lg border border-slate-700 p-4">
    <div class="text-2xl font-bold text-amber-400">{nonDeterministic().toLocaleString()}</div>
    <div class="text-sm text-slate-400">Non-deterministic</div>
  </div>
</div>

<!-- Audit Type breakdown -->
<div class="mt-4 bg-slate-800 rounded-lg border border-slate-700 p-4">
  <h3 class="text-sm font-medium text-slate-200 mb-2">Audit Type Breakdown</h3>
  <p class="text-xs text-slate-400 mb-3">
    <strong class="text-slate-200">Deterministic</strong> audits have objective pass/fail criteria.
    <strong class="text-slate-200">Non-deterministic</strong> audits require interpretation — review findings critically.
  </p>

  <!-- Progress bar -->
  <div class="h-3 rounded-full bg-slate-700 overflow-hidden flex mb-3">
    <div
      class="bg-green-500 h-full"
      style="width: {(deterministic() / stats.total) * 100}%"
      title="Deterministic: {deterministic()}"
    ></div>
    <div
      class="bg-amber-500 h-full"
      style="width: {(nonDeterministic() / stats.total) * 100}%"
      title="Non-deterministic: {nonDeterministic()}"
    ></div>
  </div>

  <div class="flex flex-wrap gap-6 text-sm">
    <div class="flex items-center gap-2">
      <span class="w-3 h-3 rounded-full bg-green-500"></span>
      <span class="text-slate-300">Deterministic: {deterministic().toLocaleString()} ({Math.round((deterministic() / stats.total) * 100)}%)</span>
    </div>
    <div class="flex items-center gap-2">
      <span class="w-3 h-3 rounded-full bg-amber-500"></span>
      <span class="text-slate-300">Non-deterministic: {nonDeterministic().toLocaleString()} ({Math.round((nonDeterministic() / stats.total) * 100)}%)</span>
    </div>
  </div>
</div>
