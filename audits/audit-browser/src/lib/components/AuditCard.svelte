<script lang="ts">
  import type { AuditInventoryRow } from '$lib/types';
  import { SDLC_PHASES } from '$lib/types';

  interface Props {
    audit: AuditInventoryRow;
    onclick?: () => void;
  }

  let { audit, onclick }: Props = $props();

  // GitHub raw file URL base
  const GITHUB_RAW_BASE = 'https://raw.githubusercontent.com/turbobeest/audits/main';
  const GITHUB_BLOB_BASE = 'https://github.com/turbobeest/audits/blob/main';

  // Generate markdown content for export
  function generateMarkdown(): string {
    const auditType = audit.fully_automated ? 'Deterministic' : 'Non-deterministic';
    const auditTypeDesc = audit.fully_automated
      ? 'Objective pass/fail criteria - results are reliable'
      : 'Requires interpretation - review findings critically';

    let phaseRestrict = 'Any Phase';
    if (audit.pre_production_only) phaseRestrict = 'Pre-Production Only';
    if (audit.production_only) phaseRestrict = 'Production Only';

    const requirements = [];
    if (audit.requires_source_code) requirements.push('Source Code');
    if (audit.requires_runtime_data) requirements.push('Runtime Data');
    if (audit.requires_production_access) requirements.push('Production Access');
    if (audit.requires_team_input) requirements.push('Team Input');
    if (audit.requires_cost_data) requirements.push('Cost Data');

    const sdlcPhases = SDLC_PHASES
      .filter(phase => audit[phase.id as keyof AuditInventoryRow] === true)
      .map(p => p.label);

    const yamlUrl = `${GITHUB_BLOB_BASE}/${audit.file_path}`;

    return `# ${audit.audit_name}

**Audit ID:** \`${audit.audit_id}\`

**Status:** ${audit.status}

## Classification

| Property | Value |
|----------|-------|
| **Category** | ${audit.category.replace(/-/g, ' ')} |
| **Subcategory** | ${audit.subcategory.replace(/-/g, ' ')} |
| **Tier** | ${audit.tier} |
| **Audit Type** | ${auditType} |
| **Phase Restriction** | ${phaseRestrict} |

> **${auditType}:** ${auditTypeDesc}

## Requirements

${requirements.length > 0 ? requirements.map(r => `- ${r}`).join('\n') : '_No special requirements_'}

## SDLC Phases

This audit applies to the following development phases:

${sdlcPhases.length > 0 ? sdlcPhases.map(p => `- ${p}`).join('\n') : '_Not specified_'}

---

📄 **Source:** [View YAML Definition](${yamlUrl})

_Generated from [Software Stack Audit Taxonomy](https://turbobeest.github.io/audits/)_
`;
  }

  // Download markdown file
  function downloadMarkdown() {
    const content = generateMarkdown();
    const blob = new Blob([content], { type: 'text/markdown' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${audit.audit_id}.md`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  }

  // Get active SDLC phases for this audit
  let activePhases = $derived(() => {
    return SDLC_PHASES.filter(phase => {
      const key = phase.id as keyof AuditInventoryRow;
      return audit[key] === true;
    });
  });

  // Get audit type - deterministic vs non-deterministic
  let auditTypeInfo = $derived(() => {
    if (audit.fully_automated) {
      return {
        label: 'Deterministic',
        color: 'text-green-400 bg-green-900/50',
        tooltip: 'Objective pass/fail criteria - results are reliable'
      };
    }
    // semi_automated or human_required = non-deterministic
    return {
      label: 'Non-deterministic',
      color: 'text-amber-400 bg-amber-900/50',
      tooltip: 'Requires interpretation - review findings critically'
    };
  });

  // Get phase restriction info
  let phaseRestriction = $derived(() => {
    if (audit.pre_production_only) return { label: 'Pre-Production Only', color: 'text-purple-400 bg-purple-900/50' };
    if (audit.production_only) return { label: 'Production Only', color: 'text-red-400 bg-red-900/50' };
    if (audit.any_phase) return { label: 'Any Phase', color: 'text-slate-400 bg-slate-700' };
    return null;
  });

  // Count requirements
  let requirementsList = $derived(() => {
    const reqs = [];
    if (audit.requires_source_code) reqs.push({ label: 'Source Code', icon: '📄', color: 'bg-slate-700' });
    if (audit.requires_runtime_data) reqs.push({ label: 'Runtime Data', icon: '📊', color: 'bg-slate-700' });
    if (audit.requires_production_access) reqs.push({ label: 'Prod Access', icon: '🔐', color: 'bg-slate-700' });
    if (audit.requires_team_input) reqs.push({ label: 'Team Input', icon: '👥', color: 'bg-slate-700' });
    if (audit.requires_cost_data) reqs.push({ label: 'Cost Data', icon: '💰', color: 'bg-slate-700' });
    // New special requirements from meta-audit
    if (audit.requires_physical_access) reqs.push({ label: 'Physical Access', icon: '🔧', color: 'bg-orange-900/50 text-orange-300' });
    if (audit.requires_human_evaluation) reqs.push({ label: 'Human Eval', icon: '👁️', color: 'bg-purple-900/50 text-purple-300' });
    if (audit.requires_interviews) reqs.push({ label: 'Interviews', icon: '🎤', color: 'bg-cyan-900/50 text-cyan-300' });
    return reqs;
  });
</script>

<!-- svelte-ignore a11y_click_events_have_key_events a11y_no_static_element_interactions -->
<div
  class="bg-slate-800 rounded-lg border border-slate-700 p-4 hover:border-blue-500 transition-colors cursor-pointer"
  onclick={onclick}
>
  <!-- Header -->
  <div class="flex items-start justify-between gap-2 mb-2">
    <h3 class="font-medium text-slate-100 leading-tight">{audit.audit_name}</h3>
    <div class="flex items-center gap-1.5 shrink-0">
      <span class="text-xs px-2 py-0.5 rounded-full {audit.status === 'active' ? 'bg-emerald-900/50 text-emerald-400' : 'bg-amber-900/50 text-amber-400'}">
        {audit.status}
      </span>
      <button
        onclick={(e) => { e.stopPropagation(); downloadMarkdown(); }}
        class="flex items-center gap-1 px-2 py-1 rounded text-xs bg-slate-700 hover:bg-slate-600 text-slate-300 hover:text-slate-100 transition-colors"
        title="Export as Markdown"
      >
        <svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
          <polyline points="7 10 12 15 17 10"/>
          <line x1="12" y1="15" x2="12" y2="3"/>
        </svg>
        Export
      </button>
    </div>
  </div>

  <!-- Category breadcrumb -->
  <div class="text-xs text-slate-400 mb-3 flex items-center gap-1">
    <span class="capitalize">{audit.category.replace(/-/g, ' ')}</span>
    <span class="text-slate-600">›</span>
    <span class="capitalize">{audit.subcategory.replace(/-/g, ' ')}</span>
  </div>

  <!-- Audit Type & Phase Restriction -->
  <div class="flex flex-wrap gap-1.5 mb-3">
    <span
      class="text-xs px-2 py-0.5 rounded {auditTypeInfo().color}"
      title={auditTypeInfo().tooltip}
    >
      {auditTypeInfo().label}
    </span>
    {#if phaseRestriction()}
      <span class="text-xs px-2 py-0.5 rounded {phaseRestriction().color}">
        {phaseRestriction().label}
      </span>
    {/if}
  </div>

  <!-- Requirements -->
  {#if requirementsList().length > 0}
    <div class="mb-3">
      <div class="text-[10px] text-slate-500 uppercase mb-1">Requires</div>
      <div class="flex flex-wrap gap-1">
        {#each requirementsList() as req}
          <span class="text-[11px] px-1.5 py-0.5 rounded {req.color || 'bg-slate-700 text-slate-300'}">
            {req.label}
          </span>
        {/each}
      </div>
    </div>
  {/if}

  <!-- SDLC Phases -->
  {#if activePhases().length > 0}
    <div>
      <div class="text-[10px] text-slate-500 uppercase mb-1">SDLC Phases</div>
      <div class="flex gap-0.5" title={activePhases().map(p => p.label).join(', ')}>
        {#each SDLC_PHASES as phase}
          {@const isActive = activePhases().some(p => p.id === phase.id)}
          <div
            class="w-2 h-2 rounded-sm {isActive ? 'bg-blue-500' : 'bg-slate-600'}"
            title={phase.label}
          ></div>
        {/each}
      </div>
      <div class="text-[10px] text-slate-500 mt-1">
        {activePhases().map(p => p.label).join(' → ')}
      </div>
    </div>
  {/if}
</div>
