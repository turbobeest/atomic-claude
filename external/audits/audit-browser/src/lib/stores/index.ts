import { writable, derived } from 'svelte/store';
import type { NavCategory, SearchFilters, AuditInventoryRow } from '$lib/types';

// Navigation state
export const navigation = writable<NavCategory[]>([]);
export const expandedCategories = writable<Set<string>>(new Set());
export const expandedSubcategories = writable<Set<string>>(new Set());

// Search and filter state
export const searchQuery = writable('');
export const filters = writable<SearchFilters>({});
export const searchResults = writable<AuditInventoryRow[]>([]);

// UI state
export const sidebarOpen = writable(true);
export const loading = writable(false);

// Derived stores
export const activeFiltersCount = derived(filters, ($filters) => {
  let count = 0;
  if ($filters.tier) count++;
  if ($filters.status) count++;
  if ($filters.category) count++;
  if ($filters.subcategory) count++;
  if ($filters.sdlcPhase) count++;
  if ($filters.automationLevel) count++;
  if ($filters.requiresSourceCode !== undefined) count++;
  if ($filters.requiresRuntimeData !== undefined) count++;
  if ($filters.requiresTeamInput !== undefined) count++;
  if ($filters.requiresProductionAccess !== undefined) count++;
  // New filters from meta-audit
  if ($filters.requiresPhysicalAccess !== undefined) count++;
  if ($filters.requiresHumanEvaluation !== undefined) count++;
  if ($filters.requiresInterviews !== undefined) count++;
  return count;
});

export const hasActiveFilters = derived(activeFiltersCount, ($count) => $count > 0);

// Actions
export function toggleCategory(categoryId: string) {
  expandedCategories.update(set => {
    const newSet = new Set(set);
    if (newSet.has(categoryId)) {
      newSet.delete(categoryId);
    } else {
      newSet.add(categoryId);
    }
    return newSet;
  });
}

export function toggleSubcategory(subcategoryId: string) {
  expandedSubcategories.update(set => {
    const newSet = new Set(set);
    if (newSet.has(subcategoryId)) {
      newSet.delete(subcategoryId);
    } else {
      newSet.add(subcategoryId);
    }
    return newSet;
  });
}

export function clearFilters() {
  filters.set({});
  searchQuery.set('');
}

export function setFilter<K extends keyof SearchFilters>(key: K, value: SearchFilters[K]) {
  filters.update(f => ({ ...f, [key]: value }));
}

export function removeFilter(key: keyof SearchFilters) {
  filters.update(f => {
    const newFilters = { ...f };
    delete newFilters[key];
    return newFilters;
  });
}

export function toggleSidebar() {
  sidebarOpen.update(open => !open);
}
