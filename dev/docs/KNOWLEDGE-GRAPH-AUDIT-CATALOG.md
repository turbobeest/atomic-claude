# Knowledge Graph Audit Catalog

> **102 audit patterns across 16 categories**
> Compiled from academic surveys (Zaveri et al., IEEE TKDE), W3C standards (SHACL, ShEx),
> graph database vendor docs, and the atomic-claude audit inventory.
>
> **Purpose**: Continuous audit loop for atomic-claude's FalkorDB knowledge graph.
> Run nightly until all applicable audits pass clean.

## Architecture: Continuous Audit Loop

```
┌──────────────────────────────────────────────────────────────────┐
│                    CONTINUOUS AUDIT LOOP                         │
│                                                                  │
│  ┌─────────────┐    ┌──────────────┐    ┌────────────────────┐  │
│  │ Audit       │───>│ Git Worktree │───>│ Opus 4.6 Gate      │  │
│  │ Engine      │    │ (isolated)   │    │                    │  │
│  │             │    │              │    │ - Review diff      │  │
│  │ - Run audit │    │ - Apply fix  │    │ - Verify intent    │  │
│  │ - Find issue│    │ - py_compile │    │ - Check regression │  │
│  │ - Propose   │    │ - Unit tests │    │                    │  │
│  │   fix       │    │              │    │                    │  │
│  └─────────────┘    └──────────────┘    └────────┬───────────┘  │
│                                                   │              │
│                                         ┌─────────┴──────────┐  │
│                                         │                    │  │
│                                    ACCEPT              REJECT   │
│                                         │                    │  │
│                                         v                    v  │
│                                  ┌────────────┐    ┌──────────┐ │
│                                  │ Merge to   │    │ Rework   │ │
│                                  │ main,      │    │ fix with │ │
│                                  │ commit,    │    │ deeper   │ │
│                                  │ push       │    │ analysis │ │
│                                  └────────────┘    └─────┬────┘ │
│                                                          │      │
│                                                     back to     │
│                                                     worktree    │
│                                                                  │
│  <---- REPEAT until all audits pass clean ---->                 │
└──────────────────────────────────────────────────────────────────┘
```

**Future state**: Ollama on 5090 GPU handles bulk audit + fix proposals.
Opus 4.6 remains the sole merge authority.

---

## Applicability Key

Each audit is marked with its applicability to atomic-claude's FalkorDB property graph:

- **[APPLY]** — Directly applicable, will be run
- **[ADAPT]** — Applicable with adaptation (RDF/SPARQL concept mapped to Cypher/property graph)
- **[SKIP]** — Not applicable to this codebase (e.g., RDF-specific, multilingual, geographic)

---

## Category 1: ACCURACY (5 checks)

| # | Audit | Applicability | Automated | LLM Required | Severity |
|---|-------|---------------|-----------|--------------|----------|
| 1.1 | Syntactic Accuracy — values conform to declared datatypes | [APPLY] | Yes | No | High |
| 1.2 | Semantic Accuracy — facts correctly represent real-world phenomena | [SKIP] | Partial | Yes | Critical |
| 1.3 | Entity Name Accuracy — labels match canonical names | [ADAPT] | Partial | Yes | Medium |
| 1.4 | Relationship Direction Accuracy — edges point correct way per schema | [APPLY] | Yes | No | High |
| 1.5 | Numerical/Quantitative Accuracy — numeric values in plausible ranges | [APPLY] | Yes | No | Medium |

## Category 2: COMPLETENESS (6 checks)

| # | Audit | Applicability | Automated | LLM Required | Severity |
|---|-------|---------------|-----------|--------------|----------|
| 2.1 | Schema Completeness — all needed classes/properties defined | [APPLY] | Partial | Yes | High |
| 2.2 | Property Completeness — ratio of missing values per property | [APPLY] | Yes | No | High |
| 2.3 | Population Completeness — % of expected entities present | [APPLY] | Partial | No | High |
| 2.4 | Interlinking Completeness — degree of cross-dataset linking | [SKIP] | Yes | No | Medium |
| 2.5 | Relationship Completeness — expected relationships exist | [APPLY] | Yes | No | High |
| 2.6 | Open-World Completeness — link prediction for missing facts | [SKIP] | Yes | No | Medium |

## Category 3: CONSISTENCY (10 checks)

| # | Audit | Applicability | Automated | LLM Required | Severity |
|---|-------|---------------|-----------|--------------|----------|
| 3.1 | Ontological Consistency — schema free of logical contradictions | [APPLY] | Yes | No | Critical |
| 3.2 | Instance-Schema Conformance — nodes match class definitions | [APPLY] | Yes | No | Critical |
| 3.3 | Cardinality Constraint Violations — correct number of values | [APPLY] | Yes | No | High |
| 3.4 | Domain/Range Violations — subjects/objects in correct classes | [APPLY] | Yes | No | High |
| 3.5 | Functional Property Violations — single-valued properties | [APPLY] | Yes | No | High |
| 3.6 | Disjointness Violations — mutually exclusive types | [ADAPT] | Yes | No | Critical |
| 3.7 | Inverse/Symmetric Relationship Consistency | [APPLY] | Yes | No | High |
| 3.8 | Transitive Closure Consistency | [ADAPT] | Yes | No | Medium |
| 3.9 | Contradictory Fact Detection | [SKIP] | Partial | Yes | Critical |
| 3.10 | Cross-Source Consistency | [SKIP] | Partial | Yes | High |

## Category 4: FRESHNESS / TIMELINESS (5 checks)

| # | Audit | Applicability | Automated | LLM Required | Severity |
|---|-------|---------------|-----------|--------------|----------|
| 4.1 | Temporal Validity — time-scoped facts still valid | [ADAPT] | Partial | No | High |
| 4.2 | Update Frequency — KG updated relative to domain change rate | [SKIP] | Yes | No | Medium |
| 4.3 | Stale Entity Detection — unmodified/unaccessed entities | [APPLY] | Yes | No | Low |
| 4.4 | Source Freshness — external sources current | [SKIP] | Partial | No | Medium |
| 4.5 | Temporal Consistency — no end dates before start dates | [APPLY] | Yes | No | High |

## Category 5: STRUCTURAL / TOPOLOGICAL (12 checks)

| # | Audit | Applicability | Automated | LLM Required | Severity |
|---|-------|---------------|-----------|--------------|----------|
| 5.1 | Orphan Node Detection — nodes with zero relationships | [APPLY] | Yes | No | Medium |
| 5.2 | Disconnected Component Analysis — graph islands | [APPLY] | Yes | No | Medium |
| 5.3 | Dangling Reference Detection — edges to non-existent nodes | [APPLY] | Yes | No | Critical |
| 5.4 | Hub/Supernode Detection — extremely high degree nodes | [APPLY] | Yes | No | Medium |
| 5.5 | Degree Distribution Analysis — anomalies in connectivity | [APPLY] | Yes | No | Low |
| 5.6 | Graph Diameter and Density — navigability metrics | [APPLY] | Yes | No | Low |
| 5.7 | Cycle Detection — unexpected cycles in hierarchies | [APPLY] | Yes | No | Critical |
| 5.8 | Relationship Type Distribution — balance across types | [APPLY] | Yes | No | Low |
| 5.9 | Class Instantiation Ratio — % of schema classes with instances | [APPLY] | Yes | No | Medium |
| 5.10 | Property Instantiation Ratio — % of defined properties used | [APPLY] | Yes | No | Medium |
| 5.11 | Centrality Anomalies — structural single points of failure | [APPLY] | Yes | No | Low |
| 5.12 | Community Structure Validation — clusters match expectations | [SKIP] | Partial | Yes | Low |

## Category 6: DUPLICATE / REDUNDANCY (5 checks)

| # | Audit | Applicability | Automated | LLM Required | Severity |
|---|-------|---------------|-----------|--------------|----------|
| 6.1 | Exact Duplicate Entity Detection — identical nodes | [APPLY] | Yes | No | High |
| 6.2 | Near-Duplicate / Fuzzy Duplicate Detection | [APPLY] | Partial | Yes | High |
| 6.3 | Redundant Relationship Detection — multiple same-type edges | [APPLY] | Yes | No | Medium |
| 6.4 | Schema Redundancy — equivalent classes/properties | [APPLY] | Partial | Yes | Medium |
| 6.5 | Data Redundancy — facts represented multiple ways | [ADAPT] | Partial | No | Medium |

## Category 7: PROVENANCE / LINEAGE (5 checks)

| # | Audit | Applicability | Automated | LLM Required | Severity |
|---|-------|---------------|-----------|--------------|----------|
| 7.1 | Source Attribution — every fact has a recorded source | [APPLY] | Yes | No | High |
| 7.2 | Transformation Lineage — processing steps recorded | [ADAPT] | Yes | No | Medium |
| 7.3 | Confidence/Trust Scoring — facts have confidence scores | [SKIP] | Yes | No | Medium |
| 7.4 | Source Reliability Assessment — source ratings current | [SKIP] | Partial | No | Medium |
| 7.5 | Audit Trail Completeness — changes logged | [APPLY] | Yes | No | High |

## Category 8: SCHEMA / ONTOLOGY QUALITY (9 checks)

| # | Audit | Applicability | Automated | LLM Required | Severity |
|---|-------|---------------|-----------|--------------|----------|
| 8.1 | Schema Satisfiability — all classes can have instances | [APPLY] | Yes | No | Critical |
| 8.2 | Class Hierarchy Depth — over/under specialization | [APPLY] | Yes | No | Low |
| 8.3 | Class Hierarchy Breadth/Balance | [SKIP] | Yes | No | Low |
| 8.4 | Property Domain/Range Specificity | [APPLY] | Yes | No | Medium |
| 8.5 | Naming Convention Compliance | [APPLY] | Yes | No | Low |
| 8.6 | Label and Description Coverage — human-readable metadata | [APPLY] | Yes | No | Medium |
| 8.7 | Multilingual Label Coverage | [SKIP] | Yes | No | Low |
| 8.8 | Schema Evolution Compatibility — backward-compatible changes | [APPLY] | Partial | No | High |
| 8.9 | Deprecated Element Usage — deprecated schema still in use | [APPLY] | Yes | No | Medium |

## Category 9: CONSTRAINT VALIDATION (9 checks)

| # | Audit | Applicability | Automated | LLM Required | Severity |
|---|-------|---------------|-----------|--------------|----------|
| 9.1 | Node Shape Compliance — nodes match declared shapes | [APPLY] | Yes | No | High |
| 9.2 | Property Shape Compliance — values match constraints | [APPLY] | Yes | No | High |
| 9.3 | Closed Shape Validation — no unexpected properties | [APPLY] | Yes | No | Medium |
| 9.4 | Pattern Constraints — string values match regex | [APPLY] | Yes | No | Medium |
| 9.5 | Value Range Constraints — numeric bounds | [APPLY] | Yes | No | Medium |
| 9.6 | String Length Constraints — min/max lengths | [APPLY] | Yes | No | Low |
| 9.7 | Value Enumeration Constraints — values from allowed set | [APPLY] | Yes | No | Medium |
| 9.8 | Custom Cypher Constraints — complex business rules | [APPLY] | Yes | No | Variable |
| 9.9 | PG-Schema Type Conformance — labels/properties/cardinalities | [APPLY] | Yes | No | High |

## Category 10: SECURITY / PRIVACY (5 checks)

| # | Audit | Applicability | Automated | LLM Required | Severity |
|---|-------|---------------|-----------|--------------|----------|
| 10.1 | PII Exposure Detection — sensitive data in graph | [APPLY] | Partial | Yes | Critical |
| 10.2 | Access Control Audit — permissions configured | [SKIP] | Yes | No | Critical |
| 10.3 | Inference Attack Vulnerability — sensitive data inferable | [SKIP] | Partial | Yes | Critical |
| 10.4 | Data Anonymization Verification | [SKIP] | Partial | No | High |
| 10.5 | Sensitive Relationship Exposure | [SKIP] | Partial | Yes | High |

## Category 11: PERFORMANCE / OPERATIONAL (6 checks)

| # | Audit | Applicability | Automated | LLM Required | Severity |
|---|-------|---------------|-----------|--------------|----------|
| 11.1 | Query Performance Profiling — latency bounds | [APPLY] | Yes | No | Medium |
| 11.2 | Index Coverage — queried properties indexed | [APPLY] | Yes | No | Medium |
| 11.3 | Traversal Depth Safety — queries constrain depth | [APPLY] | Yes | No | High |
| 11.4 | Supernode Impact Assessment — high-degree performance | [APPLY] | Yes | No | Medium |
| 11.5 | Memory/Storage Utilization | [APPLY] | Yes | No | Medium |
| 11.6 | Write Throughput / Ingestion Rate | [SKIP] | Yes | No | Medium |

## Category 12: REPRESENTATIVENESS / BIAS (5 checks)

All [SKIP] — not applicable to an SDLC pipeline knowledge graph.

## Category 13: INTEROPERABILITY / ALIGNMENT (5 checks)

| # | Audit | Applicability | Automated | LLM Required | Severity |
|---|-------|---------------|-----------|--------------|----------|
| 13.1 | Ontology Alignment Coverage | [SKIP] | Partial | Yes | Medium |
| 13.2 | URI Dereferenceability | [SKIP] | Yes | No | Medium |
| 13.3 | Standard Vocabulary Usage | [SKIP] | Partial | No | Medium |
| 13.4 | Cross-KG Entity Linking | [SKIP] | Yes | No | Low |
| 13.5 | FAIR Compliance | [SKIP] | Partial | No | Medium |

## Category 14: TEMPORAL / VERSIONING (4 checks)

| # | Audit | Applicability | Automated | LLM Required | Severity |
|---|-------|---------------|-----------|--------------|----------|
| 14.1 | Temporal Annotation Coverage — time-sensitive facts annotated | [APPLY] | Yes | No | Medium |
| 14.2 | Version History Integrity — consistent version history | [ADAPT] | Yes | No | Medium |
| 14.3 | Temporal Ordering Consistency — no anachronisms | [APPLY] | Partial | No | Medium |
| 14.4 | Invalidation Chain Integrity — superseded facts reference replacements | [ADAPT] | Yes | No | High |

## Category 15: SEMANTIC RICHNESS (4 checks)

| # | Audit | Applicability | Automated | LLM Required | Severity |
|---|-------|---------------|-----------|--------------|----------|
| 15.1 | Relationship Type Granularity — specific vs generic types | [APPLY] | Partial | Yes | Medium |
| 15.2 | Entity Type Specificity — typed at most specific level | [APPLY] | Yes | No | Medium |
| 15.3 | Blank Node Usage — excessive anonymous nodes | [SKIP] | Yes | No | Medium |
| 15.4 | Reification Overhead | [SKIP] | Yes | No | Low |

## Category 16: ANTI-PATTERNS (7 checks)

| # | Audit | Applicability | Automated | LLM Required | Severity |
|---|-------|---------------|-----------|--------------|----------|
| 16.1 | Ontology Anti-Patterns — lazy domain/range, polysemous properties | [APPLY] | Partial | Yes | Medium |
| 16.2 | Hub-and-Spoke Anti-Pattern — over-reliance on central node | [APPLY] | Yes | No | Medium |
| 16.3 | Property-as-Relationship Anti-Pattern — string props that should be edges | [APPLY] | Partial | Yes | Medium |
| 16.4 | God Node Anti-Pattern — nodes accumulating too many roles | [APPLY] | Yes | No | Medium |
| 16.5 | Dense Default Type Anti-Pattern — many entities with only generic type | [APPLY] | Yes | No | Medium |
| 16.6 | Circular Taxonomy — cycles in hierarchies | [APPLY] | Yes | No | Critical |
| 16.7 | Floating Property Anti-Pattern — defined but never used properties | [APPLY] | Yes | No | Low |

---

## Summary

| Category | Total | Applicable | Skip |
|----------|-------|-----------|------|
| 1. Accuracy | 5 | 3 | 2 |
| 2. Completeness | 6 | 4 | 2 |
| 3. Consistency | 10 | 8 | 2 |
| 4. Freshness | 5 | 3 | 2 |
| 5. Structural | 12 | 11 | 1 |
| 6. Duplicates | 5 | 5 | 0 |
| 7. Provenance | 5 | 3 | 2 |
| 8. Schema Quality | 9 | 7 | 2 |
| 9. Constraints | 9 | 9 | 0 |
| 10. Security | 5 | 1 | 4 |
| 11. Performance | 6 | 5 | 1 |
| 12. Bias | 5 | 0 | 5 |
| 13. Interop | 5 | 0 | 5 |
| 14. Temporal | 4 | 4 | 0 |
| 15. Semantic | 4 | 2 | 2 |
| 16. Anti-Patterns | 7 | 7 | 0 |
| **TOTAL** | **102** | **72** | **30** |

**72 applicable audits** will be run against the atomic-claude knowledge graph.

---

## Existing Audit Catalog Cross-Reference

72 audits from the existing `audits/audits/` directory are also relevant:
- `03-reliability-resilience/data-consistency/` — 10 audits (ACID, referential integrity, transactions)
- `08-data-state-management/data-validation/` — 6 audits (quality checks, constraints)
- `08-data-state-management/schema-design/` — 7 audits (relationships, modeling, indexes)
- `08-data-state-management/data-lineage-provenance/` — 4 audits (lineage, audit trail)
- `08-data-state-management/data-lifecycle/` — 6 audits (retention, deletion, temporal)
- `03-reliability-resilience/data-durability/` — 10 audits (redundancy, checksums, recovery)
- `06-code-quality/duplication/` — 5 audits (copy-paste, cross-module, near-duplicate)
- `06-code-quality/dead-code/` — 7 audits (unused functions, unreachable code)
- `34-business-logic-domain/domain-modeling/` — 7 audits (entity relationships, aggregates)
- `07-architecture-design/` — 5 audits (data flow, circular deps, anti-patterns)
- `06-code-quality/static-analysis/` — 4 audits (dead code, duplicates, complexity)
- `34-business-logic-domain/event-handling/` — 1 audit (event handler reliability)

---

## References

- Zaveri et al. (2015): "Quality Assessment for Linked Data: A Survey" — 18 dimensions, 69 metrics
- IEEE TKDE: "Knowledge Graph Quality Management: Comprehensive Survey"
- W3C SHACL Specification: Shapes Constraint Language
- Semantic Web Journal: "Structural Quality Metrics to Evaluate Knowledge Graphs"
- arXiv 2208.07779: "Steps to Knowledge Graphs Quality Assessment"

---

*Generated: 2026-03-07 by Opus 4.6*
*Run schedule: Nightly until all applicable audits pass clean*
