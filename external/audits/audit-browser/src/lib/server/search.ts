import MiniSearch from 'minisearch';
import type { AuditInventoryRow, SearchFilters, SearchResult } from '$lib/types';
import { loadInventory } from './dataLoader';

let searchIndex: MiniSearch<AuditInventoryRow> | null = null;

function buildSearchIndex(): MiniSearch<AuditInventoryRow> {
  if (searchIndex) return searchIndex;

  const inventory = loadInventory();

  searchIndex = new MiniSearch<AuditInventoryRow>({
    fields: ['audit_name', 'audit_id', 'category', 'subcategory'],
    storeFields: ['audit_id'],
    searchOptions: {
      boost: { audit_name: 2, audit_id: 1.5 },
      fuzzy: 0.2,
      prefix: true
    }
  });

  searchIndex.addAll(inventory.map((audit, index) => ({
    ...audit,
    id: index
  })));

  return searchIndex;
}

export function searchAudits(query: string, filters?: SearchFilters): SearchResult[] {
  const inventory = loadInventory();
  let results: AuditInventoryRow[];

  if (query.trim()) {
    const index = buildSearchIndex();
    const searchResults = index.search(query);
    const matchedIds = new Set(searchResults.map(r => inventory[r.id as number].audit_id));
    results = inventory.filter(a => matchedIds.has(a.audit_id));
  } else {
    results = [...inventory];
  }

  // Apply filters
  if (filters) {
    results = applyFilters(results, filters);
  }

  return results.map(audit => ({
    audit,
    score: 1
  }));
}

export function applyFilters(audits: AuditInventoryRow[], filters: SearchFilters): AuditInventoryRow[] {
  return audits.filter(audit => {
    // Tier filter
    if (filters.tier && audit.tier !== filters.tier) return false;

    // Status filter
    if (filters.status && audit.status !== filters.status) return false;

    // Category filter
    if (filters.category && audit.category !== filters.category) return false;

    // Subcategory filter
    if (filters.subcategory && audit.subcategory !== filters.subcategory) return false;

    // SDLC Phase filter
    if (filters.sdlcPhase) {
      const phase = filters.sdlcPhase as keyof AuditInventoryRow;
      if (!audit[phase]) return false;
    }

    // Automation level filter
    if (filters.automationLevel) {
      if (filters.automationLevel === 'fully_automated' && !audit.fully_automated) return false;
      if (filters.automationLevel === 'semi_automated' && !audit.semi_automated) return false;
      if (filters.automationLevel === 'human_required' && !audit.human_required) return false;
    }

    // Requirements filters
    if (filters.requiresSourceCode !== undefined && audit.requires_source_code !== filters.requiresSourceCode) return false;
    if (filters.requiresRuntimeData !== undefined && audit.requires_runtime_data !== filters.requiresRuntimeData) return false;
    if (filters.requiresTeamInput !== undefined && audit.requires_team_input !== filters.requiresTeamInput) return false;
    if (filters.requiresProductionAccess !== undefined && audit.requires_production_access !== filters.requiresProductionAccess) return false;

    return true;
  });
}

export function getFilterOptions() {
  const inventory = loadInventory();

  return {
    categories: [...new Set(inventory.map(a => a.category))].sort(),
    subcategories: [...new Set(inventory.map(a => a.subcategory))].sort(),
    tiers: ['focused', 'expert', 'phd', 'standard'] as const,
    statuses: ['active', 'planned'] as const,
    automationLevels: ['fully_automated', 'semi_automated', 'human_required'] as const
  };
}

export function clearSearchIndex() {
  searchIndex = null;
}
