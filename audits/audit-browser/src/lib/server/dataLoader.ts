import { readFileSync, existsSync } from 'fs';
import { parse } from 'csv-parse/sync';
import type { AuditInventoryRow, NavCategory, NavSubcategory, NavAudit } from '$lib/types';

// Use environment variable for CI/CD builds, fallback to local dev path
const AUDITS_BASE_PATH = process.env.AUDITS_BASE_PATH || '/mnt/walnut-drive/dev/audits';
const INVENTORY_PATH = `${AUDITS_BASE_PATH}/AUDIT-INVENTORY.csv`;

let cachedInventory: AuditInventoryRow[] | null = null;
let cachedNavigation: NavCategory[] | null = null;

function parseBoolean(value: string): boolean {
  return value?.toLowerCase() === 'yes';
}

export function loadInventory(): AuditInventoryRow[] {
  if (cachedInventory) return cachedInventory;

  if (!existsSync(INVENTORY_PATH)) {
    console.error(`Inventory file not found: ${INVENTORY_PATH}`);
    return [];
  }

  const csvContent = readFileSync(INVENTORY_PATH, 'utf-8');
  const records = parse(csvContent, {
    columns: true,
    skip_empty_lines: true,
    trim: true,
    relax_column_count: true
  }) as Record<string, string>[];

  cachedInventory = records.map((row): AuditInventoryRow => ({
    audit_id: row.audit_id,
    file_path: row.file_path,
    audit_name: row.audit_name,
    category: row.category,
    category_number: parseInt(row.category_number, 10),
    subcategory: row.subcategory,
    tier: row.tier as AuditInventoryRow['tier'],
    status: row.status as AuditInventoryRow['status'],
    // SDLC phases
    discovery: parseBoolean(row.discovery),
    prd: parseBoolean(row.prd),
    task_decomposition: parseBoolean(row.task_decomposition),
    specification: parseBoolean(row.specification),
    tdd: parseBoolean(row.tdd),
    implementation: parseBoolean(row.implementation),
    testing: parseBoolean(row.testing),
    integration: parseBoolean(row.integration),
    deployment: parseBoolean(row.deployment),
    post_production: parseBoolean(row.post_production),
    // Requirements
    requires_source_code: parseBoolean(row.requires_source_code),
    requires_runtime_data: parseBoolean(row.requires_runtime_data),
    requires_cost_data: parseBoolean(row.requires_cost_data),
    requires_team_input: parseBoolean(row.requires_team_input),
    requires_production_access: parseBoolean(row.requires_production_access),
    // Automation
    fully_automated: parseBoolean(row.fully_automated),
    semi_automated: parseBoolean(row.semi_automated),
    human_required: parseBoolean(row.human_required),
    // Phase restrictions
    pre_production_only: parseBoolean(row.pre_production_only),
    production_only: parseBoolean(row.production_only),
    any_phase: parseBoolean(row.any_phase)
  }));

  return cachedInventory;
}

export function buildNavigation(): NavCategory[] {
  if (cachedNavigation) return cachedNavigation;

  const inventory = loadInventory();
  const categoryMap = new Map<number, NavCategory>();

  for (const audit of inventory) {
    // Get or create category
    let category = categoryMap.get(audit.category_number);
    if (!category) {
      category = {
        id: `cat-${audit.category_number}`,
        slug: audit.category,
        title: formatCategoryTitle(audit.category),
        number: audit.category_number,
        subcategories: [],
        auditCount: 0
      };
      categoryMap.set(audit.category_number, category);
    }

    // Get or create subcategory
    let subcategory = category.subcategories.find(s => s.slug === audit.subcategory);
    if (!subcategory) {
      subcategory = {
        id: `${category.id}-${audit.subcategory}`,
        slug: audit.subcategory,
        title: formatSubcategoryTitle(audit.subcategory),
        audits: []
      };
      category.subcategories.push(subcategory);
    }

    // Add audit
    const navAudit: NavAudit = {
      id: audit.audit_id,
      slug: audit.audit_id.split('.').pop() || audit.audit_id,
      name: audit.audit_name,
      tier: audit.tier,
      status: audit.status
    };
    subcategory.audits.push(navAudit);
    category.auditCount++;
  }

  // Sort categories by number
  cachedNavigation = Array.from(categoryMap.values())
    .sort((a, b) => a.number - b.number);

  // Sort subcategories and audits alphabetically
  for (const cat of cachedNavigation) {
    cat.subcategories.sort((a, b) => a.title.localeCompare(b.title));
    for (const subcat of cat.subcategories) {
      subcat.audits.sort((a, b) => a.name.localeCompare(b.name));
    }
  }

  return cachedNavigation;
}

function formatCategoryTitle(slug: string): string {
  // Convert "security-trust" to "Security & Trust"
  return slug
    .split('-')
    .map(word => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ')
    .replace(' And ', ' & ');
}

function formatSubcategoryTitle(slug: string): string {
  // Convert "input-validation" to "Input Validation"
  return slug
    .split('-')
    .map(word => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ');
}

export function getAuditById(auditId: string): AuditInventoryRow | undefined {
  const inventory = loadInventory();
  return inventory.find(a => a.audit_id === auditId);
}

export function getAuditsByCategory(categorySlug: string): AuditInventoryRow[] {
  const inventory = loadInventory();
  return inventory.filter(a => a.category === categorySlug);
}

export function getAuditsBySubcategory(categorySlug: string, subcategorySlug: string): AuditInventoryRow[] {
  const inventory = loadInventory();
  return inventory.filter(a => a.category === categorySlug && a.subcategory === subcategorySlug);
}

export function getStats() {
  const inventory = loadInventory();

  const stats = {
    total: inventory.length,
    active: inventory.filter(a => a.status === 'active').length,
    planned: inventory.filter(a => a.status === 'planned').length,
    byTier: {
      focused: inventory.filter(a => a.tier === 'focused').length,
      expert: inventory.filter(a => a.tier === 'expert').length,
      phd: inventory.filter(a => a.tier === 'phd').length,
      standard: inventory.filter(a => a.tier === 'standard').length
    },
    byAutomation: {
      fullyAutomated: inventory.filter(a => a.fully_automated).length,
      semiAutomated: inventory.filter(a => a.semi_automated).length,
      humanRequired: inventory.filter(a => a.human_required).length
    },
    categories: new Set(inventory.map(a => a.category)).size
  };

  return stats;
}

export function clearCache() {
  cachedInventory = null;
  cachedNavigation = null;
}
