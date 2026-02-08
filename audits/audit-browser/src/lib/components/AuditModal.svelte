<script lang="ts">
  import type { AuditInventoryRow } from '$lib/types';

  interface Props {
    audit: AuditInventoryRow | null;
    onclose: () => void;
  }

  let { audit, onclose }: Props = $props();

  let yamlContent = $state<string | null>(null);
  let loading = $state(false);
  let error = $state<string | null>(null);

  const GITHUB_RAW_BASE = 'https://raw.githubusercontent.com/turbobeest/audits/main';
  const GITHUB_BLOB_BASE = 'https://github.com/turbobeest/audits/blob/main';

  // Fetch YAML content when audit changes
  $effect(() => {
    // Explicitly read audit to track dependency
    const currentAudit = audit;
    if (currentAudit) {
      loading = true;
      error = null;
      yamlContent = null;

      const url = `${GITHUB_RAW_BASE}/${currentAudit.file_path}`;
      fetch(url)
        .then(response => {
          if (!response.ok) {
            if (response.status === 404) {
              error = 'This audit definition has not been created yet (planned).';
            } else {
              error = `Failed to fetch: ${response.status} ${response.statusText}`;
            }
            return null;
          }
          return response.text();
        })
        .then(text => {
          if (text) {
            yamlContent = text;
          }
        })
        .catch(e => {
          error = `Network error: ${e instanceof Error ? e.message : 'Unknown error'}`;
        })
        .finally(() => {
          loading = false;
        });
    } else {
      yamlContent = null;
      error = null;
      loading = false;
    }
  });

  function handleKeydown(event: KeyboardEvent) {
    if (event.key === 'Escape') {
      onclose();
    }
  }

  function handleBackdropClick(event: MouseEvent) {
    if (event.target === event.currentTarget) {
      onclose();
    }
  }

  // Download YAML file
  function downloadYaml() {
    if (!yamlContent || !audit) return;
    const blob = new Blob([yamlContent], { type: 'text/yaml' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${audit.audit_id}.yaml`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  }

  // Download Markdown summary
  function downloadMarkdown() {
    if (!audit) return;
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

  function generateMarkdown(): string {
    if (!audit) return '';
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

---

**Source:** [View YAML Definition](${yamlUrl})

_Generated from [Software Stack Audit Taxonomy](https://turbobeest.github.io/audits/)_
`;
  }
</script>

<svelte:window onkeydown={handleKeydown} />

{#if audit}
  <!-- svelte-ignore a11y_click_events_have_key_events a11y_no_static_element_interactions -->
  <div
    class="fixed inset-0 bg-black/70 z-50 flex items-center justify-center p-4"
    onclick={handleBackdropClick}
  >
    <div class="bg-slate-800 rounded-lg border border-slate-600 w-full max-w-4xl max-h-[90vh] flex flex-col shadow-2xl">
      <!-- Header -->
      <div class="flex items-center justify-between p-4 border-b border-slate-700">
        <div>
          <h2 class="text-lg font-semibold text-slate-100">{audit.audit_name}</h2>
          <div class="text-sm text-slate-400 mt-0.5">
            <span class="capitalize">{audit.category.replace(/-/g, ' ')}</span>
            <span class="mx-1">›</span>
            <span class="capitalize">{audit.subcategory.replace(/-/g, ' ')}</span>
          </div>
        </div>
        <div class="flex items-center gap-2">
          <button
            onclick={downloadYaml}
            disabled={!yamlContent}
            class="flex items-center gap-1 px-3 py-1.5 text-sm bg-blue-600 hover:bg-blue-500 disabled:bg-slate-600 disabled:cursor-not-allowed text-white rounded transition-colors"
          >
            <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
              <polyline points="7 10 12 15 17 10"/>
              <line x1="12" y1="15" x2="12" y2="3"/>
            </svg>
            Export YAML
          </button>
          <button
            onclick={downloadMarkdown}
            class="flex items-center gap-1 px-3 py-1.5 text-sm bg-slate-700 hover:bg-slate-600 text-slate-200 rounded transition-colors"
          >
            <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
              <polyline points="7 10 12 15 17 10"/>
              <line x1="12" y1="15" x2="12" y2="3"/>
            </svg>
            Export MD
          </button>
          <a
            href="{GITHUB_BLOB_BASE}/{audit.file_path}"
            target="_blank"
            rel="noopener noreferrer"
            class="px-3 py-1.5 text-sm bg-slate-700 hover:bg-slate-600 text-slate-200 rounded transition-colors"
          >
            GitHub
          </a>
          <button
            onclick={onclose}
            class="p-1.5 hover:bg-slate-700 rounded text-slate-400 hover:text-slate-200 transition-colors"
            title="Close"
          >
            <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <line x1="18" y1="6" x2="6" y2="18"></line>
              <line x1="6" y1="6" x2="18" y2="18"></line>
            </svg>
          </button>
        </div>
      </div>

      <!-- Content -->
      <div class="flex-1 overflow-auto p-4">
        {#if loading}
          <div class="flex items-center justify-center py-12">
            <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500"></div>
            <span class="ml-3 text-slate-400">Loading audit definition...</span>
          </div>
        {:else if error}
          <div class="bg-amber-900/30 border border-amber-700 rounded-lg p-4">
            <div class="flex items-start gap-3">
              <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="text-amber-400 shrink-0 mt-0.5">
                <circle cx="12" cy="12" r="10"></circle>
                <line x1="12" y1="8" x2="12" y2="12"></line>
                <line x1="12" y1="16" x2="12.01" y2="16"></line>
              </svg>
              <div>
                <p class="text-amber-200">{error}</p>
                {#if audit.status === 'planned'}
                  <p class="text-slate-400 text-sm mt-2">
                    This audit is planned but the YAML file hasn't been created yet.
                    Check back later or contribute to the project!
                  </p>
                {/if}
              </div>
            </div>
          </div>
        {:else if yamlContent}
          <pre class="text-sm text-slate-300 bg-slate-900 rounded-lg p-4 overflow-x-auto font-mono leading-relaxed whitespace-pre-wrap">{yamlContent}</pre>
        {:else}
          <div class="flex items-center justify-center py-12">
            <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500"></div>
            <span class="ml-3 text-slate-400">Initializing...</span>
          </div>
        {/if}
      </div>

      <!-- Footer -->
      <div class="flex items-center justify-between p-4 border-t border-slate-700 bg-slate-800/50">
        <div class="text-xs text-slate-500">
          <code>{audit.audit_id}</code>
        </div>
        <div class="flex items-center gap-2">
          <span class="text-xs px-2 py-0.5 rounded-full {audit.status === 'active' ? 'bg-emerald-900/50 text-emerald-400' : 'bg-amber-900/50 text-amber-400'}">
            {audit.status}
          </span>
          <span class="text-xs px-2 py-0.5 rounded bg-slate-700 text-slate-300">
            {audit.tier}
          </span>
        </div>
      </div>
    </div>
  </div>
{/if}
