# Agent Tier Classification

This document classifies all 162 agents into the three context-optimized tiers.

## Tier Definitions

| Tier | Tokens | Instructions | Model | Use Case |
|------|--------|--------------|-------|----------|
| **Focused** | ~500 | 5-10 | sonnet/haiku | Bounded tasks with clear scope |
| **Expert** | ~1500 | 15-20 | sonnet/opus | Specialized domain work |
| **PhD** | ~3000 | 25-35 | opus (required) | Deep, complex challenges |

---

## Focused Tier (~500 tokens)

*Bounded tasks with clear scope, 5-10 instructions*

| Agent | Category | Rationale |
|-------|----------|-----------|
| `validation-depth-controller` | Orchestration | Single purpose: validate against schema |
| `assignment-agent` | Orchestration | Focused: assign tasks, set priorities |
| `frontend-developer` | Development | Implementation-focused, clear patterns |
| `mobile-developer` | Frontend | Implementation-focused |
| `database-admin` | Data | Operational tasks, clear procedures |
| `rust-safety-validator` | Security | Single focus: unsafe code detection |
| `compliance-checker` | Security | Checklist-driven verification |
| `memory-optimizer` | Performance | Narrow scope: memory analysis |
| `cache-expert` | Performance | Focused domain: caching strategies |

**Total: 9 agents**

---

## Expert Tier (~1500 tokens)

*Specialized domain work, 15-20 instructions*

### Orchestration Intelligence

| Agent | Subcategory | Rationale |
|-------|-------------|-----------|
| `orchestrator` | Core | Complex coordination, well-defined patterns |
| `agent-selector` | Core | Domain expertise in agent matching |
| `collaborator-coordinator` | Core | Multi-agent coordination patterns |
| `planning-agent` | Planning | Task planning depth |
| `taskmaster-integrator` | Planning | TaskMaster domain expertise |
| `documentation-curator` | Knowledge | Research and synthesis skills |

### Development Architecture

| Agent | Subcategory | Rationale |
|-------|-------------|-----------|
| `architect-reviewer` | Architecture | Architectural pattern knowledge |
| `backend-architect` | Architecture | System design expertise |
| `graphql-architect` | Architecture | GraphQL-specific depth |
| `ui-ux-designer` | UX | UX principles and patterns |

### Backend Ecosystems - Systems Languages

| Agent | Rationale |
|-------|-----------|
| `rust-pro` | Ownership, lifetimes, safety patterns |
| `golang-pro` | Concurrency, interfaces, idioms |
| `c-pro` | Memory management, systems programming |
| `cpp-pro` | Templates, RAII, modern C++ |

### Backend Ecosystems - Application Languages

| Agent | Rationale |
|-------|-----------|
| `python-pro` | Pythonic patterns, ecosystem depth |
| `javascript-pro` | Async, prototypes, ecosystem |
| `typescript-pro` | Type system, patterns |

### Backend Ecosystems - Enterprise Languages

| Agent | Rationale |
|-------|-----------|
| `java-pro` | Enterprise patterns, JVM expertise |
| `csharp-pro` | .NET ecosystem, patterns |
| `scala-pro` | Functional + OOP, type system |

### Backend Ecosystems - Dynamic Languages

| Agent | Rationale |
|-------|-----------|
| `ruby-pro` | Metaprogramming, Rails patterns |
| `php-pro` | Web patterns, frameworks |
| `elixir-pro` | OTP, concurrency, fault tolerance |

### Frontend Ecosystems - JavaScript Frameworks

| Agent | Rationale |
|-------|-----------|
| `reactjs-expert` | React patterns, hooks, state management |
| `nextjs-expert` | SSR, routing, optimization |
| `svelte-expert` | Svelte-specific patterns |

### Frontend Ecosystems - Mobile Development

| Agent | Rationale |
|-------|-----------|
| `flutter-expert` | Cross-platform, Dart patterns |
| `ios-developer` | Swift, UIKit/SwiftUI |

### Data Intelligence - Database Systems

| Agent | Rationale |
|-------|-----------|
| `neo4j-expert` | Graph patterns, Cypher optimization |
| `falkordb-expert` | Graph-specific optimization |
| `sql-pro` | Query optimization, schema design |

### Data Intelligence - Database Operations

| Agent | Rationale |
|-------|-----------|
| `database-optimizer` | Performance tuning expertise |

### Data Intelligence - Data Processing

| Agent | Rationale |
|-------|-----------|
| `data-engineer` | Pipeline architecture |
| `data-scientist` | ML workflows, statistical analysis |

### Data Intelligence - Machine Learning

| Agent | Rationale |
|-------|-----------|
| `ai-engineer` | AI system design |
| `ml-engineer` | Model training, deployment |
| `mlops-engineer` | ML infrastructure |

### Data Intelligence - GPU Computing

| Agent | Rationale |
|-------|-----------|
| `cuda-expert` | GPU programming patterns |
| `rapids-expert` | GPU data science |
| `jetson-expert` | Edge AI deployment |
| `isaac-expert` | Robotics simulation |

### Infrastructure Security - Cloud Platforms

| Agent | Rationale |
|-------|-----------|
| `aws-expert` | AWS services, well-architected patterns |
| `gcp-expert` | GCP services, patterns |
| `azure-expert` | Azure services, patterns |

### Infrastructure Security - Containerization

| Agent | Rationale |
|-------|-----------|
| `docker-expert` | Container patterns, optimization |
| `kubernetes-expert` | K8s architecture, operators |

### Infrastructure Security - Infrastructure as Code

| Agent | Rationale |
|-------|-----------|
| `terraform-expert` | IaC patterns, state management |
| `ansible-expert` | Configuration management |
| `pulumi-expert` | IaC with programming languages |

### Infrastructure Security - Monitoring & Observability

| Agent | Rationale |
|-------|-----------|
| `prometheus-expert` | Metrics, alerting patterns |
| `grafana-expert` | Visualization, dashboards |
| `elk-expert` | Log aggregation, search |

### Infrastructure Security - Security & Compliance

| Agent | Rationale |
|-------|-----------|
| `security-auditor` | OWASP, threat modeling, CVE knowledge |
| `penetration-tester` | Attack vectors, exploitation techniques |

### Immersive & Spatial - Augmented Reality

| Agent | Rationale |
|-------|-----------|
| `arkit-expert` | ARKit-specific patterns |
| `arcore-expert` | ARCore-specific patterns |

### Immersive & Spatial - 3D Visualization

| Agent | Rationale |
|-------|-----------|
| `cesiumjs-expert` | Geospatial visualization |
| `unity-developer` | Unity patterns, C# integration |
| `omniverse-expert` | NVIDIA Omniverse ecosystem |

### Specialized Domains - Blockchain & Web3

| Agent | Rationale |
|-------|-----------|
| `solidity-expert` | Smart contract patterns, security |
| `web3-developer` | dApp development patterns |

### Specialized Domains - Game Development

| Agent | Rationale |
|-------|-----------|
| `unreal-developer` | Unreal patterns, Blueprints, C++ |
| `godot-expert` | Godot-specific patterns |
| `game-designer` | Game design principles |

### Specialized Domains - Scientific Computing

| Agent | Rationale |
|-------|-----------|
| `matlab-expert` | MATLAB patterns, toolboxes |
| `r-statistician` | Statistical analysis |
| `julia-expert` | Scientific computing |

### Specialized Domains - Performance Optimization

| Agent | Rationale |
|-------|-----------|
| `performance-engineer` | Profiling, optimization strategies |

**Total: ~140 agents**

---

## PhD Tier (~3000 tokens)

*Deep, complex challenges requiring research-level expertise, opus model required*

### Pre-defined PhD Agents

| Agent | Category | Rationale |
|-------|----------|-----------|
| `first-principles-engineer` | Orchestration | Fundamental reasoning, novel problem decomposition |
| `defi-architect` | Blockchain | Complex financial systems, game theory, economic attacks |
| `octree-voxel-expert` | 3D/Spatial | Advanced spatial data structures, algorithmic depth |

### When to Create PhD Agents

PhD tier agents should be **created on-demand** via the `agent-inventor` skill for:

1. **Novel domain combinations**
   - WebSocket + GraphQL + Real-time Collaboration
   - Security + ML + Distributed Systems
   - Embedded + Safety-Critical + Formal Verification

2. **Edge-case problems**
   - When standard experts hit their limits
   - Unusual technology combinations
   - Legacy system modernization

3. **Research-level challenges**
   - Formal verification
   - Theorem proving
   - Novel algorithm design

4. **Cross-domain synthesis**
   - Problems requiring multiple deep specializations
   - Architectural decisions with novel constraints

5. **Project-specific deep expertise**
   - Domain corpora requiring PhD-level interpretation
   - Regulatory/compliance domains with extensive requirements
   - Industry-specific knowledge bases

**Total: 3 pre-defined + on-demand creation**

---

## Summary Statistics

| Tier | Count | Percentage | Model |
|------|-------|------------|-------|
| Focused | 9 | 6% | sonnet/haiku |
| Expert | ~140 | 86% | sonnet/opus |
| PhD | 3 + on-demand | 8% | opus (required) |

---

## Refactoring Priority

### Phase 1: Focused Tier (Quickest)
Refactor these first to establish the pattern:
1. `validation-depth-controller`
2. `assignment-agent`
3. `compliance-checker`
4. `rust-safety-validator`

### Phase 2: High-Use Experts
Refactor most commonly used agents:
1. `orchestrator`
2. `security-auditor`
3. `architect-reviewer`
4. `typescript-pro`
5. `python-pro`
6. `kubernetes-expert`
7. `docker-expert`

### Phase 3: Remaining Experts
Refactor by category, starting with most complete categories.

### Phase 4: PhD Agents
PhD agents are primarily created on-demand. The three pre-defined ones can be refactored last.

---

## Notes

- **Expert is the default tier** - most agents require domain depth but have established patterns
- **PhD tier is intentionally sparse** - created for specific project needs, not maintained generically
- **Focused tier is for clear, bounded tasks** - if an agent needs domain depth, it's Expert tier
- **Model selection matters** - PhD requires opus; Expert can use sonnet or opus based on stakes
