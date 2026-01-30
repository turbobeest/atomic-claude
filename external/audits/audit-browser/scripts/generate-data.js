#!/usr/bin/env node
/**
 * Generate static JSON data file for the audit browser.
 * This runs at build time to embed audit data in the static site.
 */

import { readFileSync, writeFileSync, mkdirSync, existsSync } from 'fs';
import { parse } from 'csv-parse/sync';
import { dirname, join } from 'path';
import { fileURLToPath } from 'url';

const __dirname = dirname(fileURLToPath(import.meta.url));

// Use environment variable or default path
const AUDITS_BASE_PATH = process.env.AUDITS_BASE_PATH || join(__dirname, '..', '..');
const INVENTORY_PATH = join(AUDITS_BASE_PATH, 'AUDIT-INVENTORY.csv');
const OUTPUT_DIR = join(__dirname, '..', 'static', 'data');
const OUTPUT_PATH = join(OUTPUT_DIR, 'audits.json');

function parseBoolean(value) {
  return value?.toLowerCase() === 'yes';
}

function loadInventory() {
  if (!existsSync(INVENTORY_PATH)) {
    console.error(`Inventory file not found: ${INVENTORY_PATH}`);
    process.exit(1);
  }

  const csvContent = readFileSync(INVENTORY_PATH, 'utf-8');
  const records = parse(csvContent, {
    columns: true,
    skip_empty_lines: true,
    trim: true,
    relax_column_count: true
  });

  return records.map((row) => ({
    audit_id: row.audit_id,
    file_path: row.file_path,
    audit_name: row.audit_name,
    category: row.category,
    category_number: parseInt(row.category_number, 10),
    subcategory: row.subcategory,
    tier: row.tier,
    status: row.status,
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
}

function formatCategoryTitle(slug) {
  return slug
    .split('-')
    .map(word => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ')
    .replace(' And ', ' & ');
}

function formatSubcategoryTitle(slug) {
  return slug
    .split('-')
    .map(word => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ');
}

function buildNavigation(inventory) {
  const categoryMap = new Map();

  for (const audit of inventory) {
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

    subcategory.audits.push({
      id: audit.audit_id,
      slug: audit.audit_id.split('.').pop() || audit.audit_id,
      name: audit.audit_name,
      tier: audit.tier,
      status: audit.status
    });
    category.auditCount++;
  }

  const navigation = Array.from(categoryMap.values())
    .sort((a, b) => a.number - b.number);

  for (const cat of navigation) {
    cat.subcategories.sort((a, b) => a.title.localeCompare(b.title));
    for (const subcat of cat.subcategories) {
      subcat.audits.sort((a, b) => a.name.localeCompare(b.name));
    }
  }

  return navigation;
}

function getStats(inventory) {
  return {
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
}

function getFilterOptions(inventory) {
  return {
    categories: [...new Set(inventory.map(a => a.category))].sort(),
    subcategories: [...new Set(inventory.map(a => a.subcategory))].sort(),
    tiers: ['focused', 'expert', 'phd', 'standard'],
    statuses: ['active', 'planned'],
    automationLevels: ['fully_automated', 'semi_automated', 'human_required']
  };
}

// Main
console.log('Generating audit data...');
console.log(`Reading from: ${INVENTORY_PATH}`);

const inventory = loadInventory();
const navigation = buildNavigation(inventory);
const stats = getStats(inventory);
const filterOptions = getFilterOptions(inventory);

const data = {
  audits: inventory,
  navigation,
  stats,
  filterOptions
};

// Ensure output directory exists
if (!existsSync(OUTPUT_DIR)) {
  mkdirSync(OUTPUT_DIR, { recursive: true });
}

writeFileSync(OUTPUT_PATH, JSON.stringify(data));

console.log(`Generated ${OUTPUT_PATH}`);
console.log(`  - ${inventory.length} audits`);
console.log(`  - ${navigation.length} categories`);
console.log(`  - ${stats.active} active, ${stats.planned} planned`);
