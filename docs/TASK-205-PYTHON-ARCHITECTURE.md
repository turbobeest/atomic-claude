# Task 205 Python Architecture - Modular Design for Experimentation

**Date**: 2026-02-05
**Status**: DESIGN PROPOSAL
**Goal**: Zero-tech-debt architecture with pluggable components

---

## Design Philosophy

**Problem**: Current bash implementation locks us into:
- claude-mem for memory
- Guardian validation pattern
- Adaptive context management
- 8-generation workflow

**Risk**: If performance is unacceptable, we're stuck with tech debt

**Solution**: Plugin-based architecture where every major component is swappable at runtime via configuration

---

## Core Architectural Principles

### 1. Everything is a Plugin

```python
# Not this (hardcoded):
from claude_mem import memory_recall_local
result = memory_recall_local(keywords, phase)

# But this (pluggable):
from prd_authoring.plugins import get_plugin
memory_backend = get_plugin('memory', config.memory_backend)
result = memory_backend.recall(keywords, phase)
```

### 2. Configuration-Driven Behavior

```yaml
# prd-config.yaml
memory:
  backend: claude-mem  # or: simple-file, sqlite, redis, mcp-memory

guardian:
  enabled: true
  provider: ollama  # or: disabled, bedrock, api
  strategy: structured-context  # or: full-context, minimal, adaptive

context:
  strategy: adaptive  # or: full, structured, minimal, hybrid

workflow:
  type: 8-generation-sequential  # or: 15-section-parallel, hybrid-streaming
```

### 3. Interface-First Design

Every component has a clear contract (Protocol/ABC), multiple implementations

### 4. Metrics & Observability

Built-in instrumentation to measure what works:
```python
@metrics.track('generation_time')
@metrics.track('token_usage')
def generate_section(gen_num, prompt, context):
    ...
```

### 5. A/B Testing Ready

```python
# Run same generation with different strategies, compare
if config.ab_test_enabled:
    result_a = generate_with_strategy('current')
    result_b = generate_with_strategy('experimental')
    metrics.compare(result_a, result_b)
    return result_a if result_a.score > result_b.score else result_b
```

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                    PRDOrchestrator                          │
│  (Coordinates workflow, doesn't know implementation details)│
└─────────────────────────────────────────────────────────────┘
                          │
          ┌───────────────┼───────────────┐
          │               │               │
          ▼               ▼               ▼
    ┌─────────┐    ┌───────────┐   ┌──────────┐
    │ Memory  │    │  Context  │   │ Guardian │
    │ Plugin  │    │  Plugin   │   │  Plugin  │
    └─────────┘    └───────────┘   └──────────┘
          │               │               │
    ┌─────┴────┐    ┌─────┴────┐   ┌─────┴────┐
    │ claude-  │    │ adaptive │   │ ollama   │
    │ mem      │    │ strategy │   │ validator│
    │          │    │          │   │          │
    ├──────────┤    ├──────────┤   ├──────────┤
    │ sqlite   │    │ full     │   │ disabled │
    │ backend  │    │ strategy │   │          │
    │          │    │          │   │          │
    ├──────────┤    ├──────────┤   ├──────────┤
    │ redis    │    │ minimal  │   │ bedrock  │
    │ backend  │    │ strategy │   │ validator│
    └──────────┘    └──────────┘   └──────────┘
```

---

## Component Interfaces

### 1. Memory Backend Protocol

```python
from typing import Protocol, List, Dict, Optional
from dataclasses import dataclass

@dataclass
class MemoryArtifact:
    content: str
    source: str
    timestamp: str
    relevance_score: Optional[float] = None

class MemoryBackend(Protocol):
    """Abstract interface for memory storage/retrieval"""

    def save(self, phase: int, task: str, key: str, content: str) -> bool:
        """Save artifact to memory"""
        ...

    def recall(self, keywords: List[str], phase: int) -> List[MemoryArtifact]:
        """Recall artifacts matching keywords from specific phase"""
        ...

    def recall_all(self, phase: int) -> List[MemoryArtifact]:
        """Recall all artifacts from phase"""
        ...

    def health_check(self) -> bool:
        """Check if backend is available"""
        ...
```

**Implementations**:
```python
# claude_mem_backend.py
class ClaudeMemBackend(MemoryBackend):
    """Current bash implementation (wraps lib/memory.sh)"""
    def recall(self, keywords, phase):
        # Call _memory_recall_local via subprocess
        ...

# sqlite_backend.py
class SQLiteMemoryBackend(MemoryBackend):
    """Local SQLite database with FTS5 search"""
    def recall(self, keywords, phase):
        # Full-text search in SQLite
        ...

# mcp_memory_backend.py
class MCPMemoryBackend(MemoryBackend):
    """MCP memory server (future)"""
    def recall(self, keywords, phase):
        # Call MCP memory tool
        ...

# simple_file_backend.py
class SimpleFileBackend(MemoryBackend):
    """Simple file-based storage (no dependencies)"""
    def recall(self, keywords, phase):
        # Grep through .state/memory/ files
        ...
```

**Usage**:
```python
# Swap memory backend via config
memory = get_plugin('memory', config.memory.backend)
artifacts = memory.recall(['goals', 'user_needs'], phase=1)
```

---

### 2. Context Strategy Protocol

```python
from typing import Protocol, Literal

ContextStrategyType = Literal['full', 'structured', 'minimal', 'adaptive']

@dataclass
class ContextConfig:
    gen_num: int
    prior_sections: str
    model_name: str
    strategy_type: ContextStrategyType

@dataclass
class ContextResult:
    content: str
    token_estimate: int
    strategy_used: str
    metadata: Dict[str, any]

class ContextStrategy(Protocol):
    """Abstract interface for context extraction"""

    def extract(self, config: ContextConfig) -> ContextResult:
        """Extract context from prior sections"""
        ...

    def estimate_tokens(self, content: str) -> int:
        """Estimate token count for content"""
        ...
```

**Implementations**:
```python
# full_context_strategy.py
class FullContextStrategy(ContextStrategy):
    """Include complete prior sections (large models)"""
    def extract(self, config):
        return ContextResult(
            content=config.prior_sections,
            token_estimate=len(config.prior_sections) * 0.3,
            strategy_used='full'
        )

# structured_context_strategy.py
class StructuredContextStrategy(ContextStrategy):
    """Extract structured elements (current implementation)"""
    def extract(self, config):
        # Extract headings, tech stack, FR/NFR lists
        ...

# minimal_context_strategy.py
class MinimalContextStrategy(ContextStrategy):
    """IDs and headings only (small models)"""
    def extract(self, config):
        # Extract only IDs
        ...

# adaptive_context_strategy.py
class AdaptiveContextStrategy(ContextStrategy):
    """Selects sub-strategy based on model"""
    def extract(self, config):
        window = detect_model_window(config.model_name)
        if window >= 100000:
            strategy = FullContextStrategy()
        elif window >= 30000:
            strategy = StructuredContextStrategy()
        else:
            strategy = MinimalContextStrategy()
        return strategy.extract(config)

# hybrid_context_strategy.py (EXPERIMENTAL)
class HybridContextStrategy(ContextStrategy):
    """Uses semantic search to find relevant prior content"""
    def extract(self, config):
        # Use embeddings to find relevant sections
        # More efficient than full content, better than structured
        ...
```

---

### 3. Guardian Validator Protocol

```python
from typing import Protocol, Literal

GuardianStatus = Literal['pass', 'warn', 'fail']

@dataclass
class ValidationConfig:
    gen_num: int
    generated_content: str
    prior_context: str
    project_context: str
    model: str

@dataclass
class ValidationResult:
    status: GuardianStatus
    issues: List[Dict[str, str]]
    context_injection: Dict[str, List[str]]
    metadata: Dict[str, any]

class GuardianValidator(Protocol):
    """Abstract interface for guardian validation"""

    def validate(self, config: ValidationConfig) -> ValidationResult:
        """Validate generated content"""
        ...

    def should_retry(self, result: ValidationResult, attempt: int) -> bool:
        """Determine if generation should be retried"""
        ...
```

**Implementations**:
```python
# ollama_guardian.py
class OllamaGuardian(GuardianValidator):
    """Current guardian implementation"""
    def validate(self, config):
        # Call Ollama model for validation
        ...

# disabled_guardian.py
class DisabledGuardian(GuardianValidator):
    """No-op guardian for fast iteration"""
    def validate(self, config):
        return ValidationResult(status='pass', issues=[], context_injection={})

# bedrock_guardian.py
class BedrockGuardian(GuardianValidator):
    """Use Bedrock Haiku for validation"""
    def validate(self, config):
        # Call Bedrock with fast model
        ...

# rule_based_guardian.py (EXPERIMENTAL)
class RuleBasedGuardian(GuardianValidator):
    """Fast rule-based validation (no LLM call)"""
    def validate(self, config):
        issues = []
        # Check ID sequences
        if not check_fr_sequence(config.generated_content):
            issues.append({'severity': 'critical', 'message': 'FR gap detected'})
        # Check tech stack consistency
        ...
        return ValidationResult(
            status='fail' if issues else 'pass',
            issues=issues
        )

# hybrid_guardian.py (EXPERIMENTAL)
class HybridGuardian(GuardianValidator):
    """Rules first, LLM only if rules fail"""
    def validate(self, config):
        rule_result = RuleBasedGuardian().validate(config)
        if rule_result.status == 'pass':
            return rule_result  # Fast path
        # Rules failed, escalate to LLM
        return OllamaGuardian().validate(config)
```

---

### 4. Workflow Orchestrator Protocol

```python
class WorkflowOrchestrator(Protocol):
    """Abstract interface for PRD generation workflow"""

    def execute(self, config: PRDConfig) -> PRDResult:
        """Execute complete PRD generation workflow"""
        ...

    def resume(self, checkpoint: str) -> PRDResult:
        """Resume from checkpoint"""
        ...
```

**Implementations**:
```python
# sequential_8gen_workflow.py
class Sequential8GenWorkflow(WorkflowOrchestrator):
    """Current 8-generation sequential approach"""
    def execute(self, config):
        for gen_num in range(1, 9):
            self.generate_section(gen_num)
            self.validate_with_guardian(gen_num)
            self.save_to_memory(gen_num)
        return self.assemble_prd()

# parallel_15section_workflow.py (EXPERIMENTAL)
class Parallel15SectionWorkflow(WorkflowOrchestrator):
    """Generate all 15 sections in parallel"""
    def execute(self, config):
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(self.generate_section, i)
                      for i in range(15)]
            results = [f.result() for f in futures]
        return self.assemble_prd(results)

# streaming_workflow.py (EXPERIMENTAL)
class StreamingWorkflow(WorkflowOrchestrator):
    """Stream PRD generation (no waiting for full sections)"""
    def execute(self, config):
        for section_chunk in self.stream_generate():
            yield section_chunk
            self.validate_chunk(section_chunk)
```

---

## Plugin Registry & Configuration

### Plugin Registry

```python
# prd_authoring/plugins/__init__.py
from typing import Dict, Type, Protocol

class PluginRegistry:
    """Central registry for all plugins"""

    _memory_backends: Dict[str, Type[MemoryBackend]] = {}
    _context_strategies: Dict[str, Type[ContextStrategy]] = {}
    _guardian_validators: Dict[str, Type[GuardianValidator]] = {}
    _workflow_orchestrators: Dict[str, Type[WorkflowOrchestrator]] = {}

    @classmethod
    def register_memory(cls, name: str, backend: Type[MemoryBackend]):
        cls._memory_backends[name] = backend

    @classmethod
    def get_memory(cls, name: str) -> MemoryBackend:
        if name not in cls._memory_backends:
            raise ValueError(f"Unknown memory backend: {name}")
        return cls._memory_backends[name]()

    # Similar for other plugin types...

# Auto-register plugins
def register_all_plugins():
    # Memory backends
    PluginRegistry.register_memory('claude-mem', ClaudeMemBackend)
    PluginRegistry.register_memory('sqlite', SQLiteMemoryBackend)
    PluginRegistry.register_memory('simple-file', SimpleFileBackend)
    PluginRegistry.register_memory('mcp', MCPMemoryBackend)

    # Context strategies
    PluginRegistry.register_context('full', FullContextStrategy)
    PluginRegistry.register_context('structured', StructuredContextStrategy)
    PluginRegistry.register_context('minimal', MinimalContextStrategy)
    PluginRegistry.register_context('adaptive', AdaptiveContextStrategy)
    PluginRegistry.register_context('hybrid', HybridContextStrategy)

    # Guardian validators
    PluginRegistry.register_guardian('ollama', OllamaGuardian)
    PluginRegistry.register_guardian('disabled', DisabledGuardian)
    PluginRegistry.register_guardian('bedrock', BedrockGuardian)
    PluginRegistry.register_guardian('rule-based', RuleBasedGuardian)
    PluginRegistry.register_guardian('hybrid', HybridGuardian)

    # Workflows
    PluginRegistry.register_workflow('8-gen-sequential', Sequential8GenWorkflow)
    PluginRegistry.register_workflow('15-section-parallel', Parallel15SectionWorkflow)
    PluginRegistry.register_workflow('streaming', StreamingWorkflow)
```

### Configuration System

```python
# prd_authoring/config.py
from dataclasses import dataclass
from typing import Optional
import yaml

@dataclass
class MemoryConfig:
    backend: str = 'claude-mem'
    cache_ttl: int = 3600
    fallback_backend: Optional[str] = 'simple-file'

@dataclass
class GuardianConfig:
    enabled: bool = True
    provider: str = 'ollama'
    model: str = 'llama3.3:70b'
    max_retries: int = 2
    timeout: int = 180

@dataclass
class ContextConfig:
    strategy: str = 'adaptive'
    max_tokens: int = 100000

@dataclass
class WorkflowConfig:
    type: str = '8-gen-sequential'
    parallel_sections: bool = False
    checkpoint_enabled: bool = True

@dataclass
class PRDConfig:
    memory: MemoryConfig
    guardian: GuardianConfig
    context: ContextConfig
    workflow: WorkflowConfig

    @classmethod
    def from_yaml(cls, path: str) -> 'PRDConfig':
        with open(path) as f:
            data = yaml.safe_load(f)
        return cls(
            memory=MemoryConfig(**data.get('memory', {})),
            guardian=GuardianConfig(**data.get('guardian', {})),
            context=ContextConfig(**data.get('context', {})),
            workflow=WorkflowConfig(**data.get('workflow', {}))
        )

    @classmethod
    def from_env(cls) -> 'PRDConfig':
        """Load config from environment variables (12-factor app)"""
        return cls(
            memory=MemoryConfig(
                backend=os.getenv('PRD_MEMORY_BACKEND', 'claude-mem')
            ),
            guardian=GuardianConfig(
                enabled=os.getenv('PRD_GUARDIAN_ENABLED', 'true').lower() == 'true',
                provider=os.getenv('PRD_GUARDIAN_PROVIDER', 'ollama')
            ),
            # ...
        )
```

---

## Metrics & Observability

### Metrics Collection

```python
# prd_authoring/metrics.py
from typing import Dict, List, Callable
from dataclasses import dataclass, field
from datetime import datetime
import time

@dataclass
class Metric:
    name: str
    value: float
    timestamp: datetime
    labels: Dict[str, str] = field(default_factory=dict)

class MetricsCollector:
    """Collect metrics during PRD generation"""

    def __init__(self):
        self.metrics: List[Metric] = []

    def record(self, name: str, value: float, **labels):
        self.metrics.append(Metric(
            name=name,
            value=value,
            timestamp=datetime.now(),
            labels=labels
        ))

    def timer(self, name: str, **labels):
        """Context manager for timing operations"""
        return Timer(self, name, labels)

    def summary(self) -> Dict[str, any]:
        """Generate metrics summary"""
        return {
            'total_time': self._sum_metric('generation_time'),
            'token_usage': self._sum_metric('token_usage'),
            'guardian_validations': self._count_metric('guardian_validation'),
            'memory_recalls': self._count_metric('memory_recall'),
            # ...
        }

class Timer:
    def __init__(self, collector: MetricsCollector, name: str, labels: Dict):
        self.collector = collector
        self.name = name
        self.labels = labels
        self.start_time = None

    def __enter__(self):
        self.start_time = time.time()
        return self

    def __exit__(self, *args):
        elapsed = time.time() - self.start_time
        self.collector.record(self.name, elapsed, **self.labels)

# Usage
metrics = MetricsCollector()

with metrics.timer('generation', gen_num=1, provider='bedrock'):
    result = generate_section(1)

metrics.record('token_usage', result.token_count, gen_num=1)
```

### Performance Comparison

```python
# prd_authoring/experiments.py
class ExperimentRunner:
    """Run A/B tests on different configurations"""

    def compare_memory_backends(self):
        """Compare memory backend performance"""
        configs = [
            PRDConfig(memory=MemoryConfig(backend='claude-mem')),
            PRDConfig(memory=MemoryConfig(backend='sqlite')),
            PRDConfig(memory=MemoryConfig(backend='simple-file')),
        ]

        results = []
        for config in configs:
            with metrics.timer('full_prd', backend=config.memory.backend):
                result = run_prd_generation(config)
            results.append({
                'backend': config.memory.backend,
                'time': metrics.last_duration,
                'quality_score': result.quality_score
            })

        return self.analyze_results(results)

    def compare_guardian_strategies(self):
        """Compare guardian validation strategies"""
        strategies = ['ollama', 'disabled', 'rule-based', 'hybrid']
        # Run same PRD generation with different guardians
        # Compare: time, quality, validation accuracy
        ...
```

---

## Usage Examples

### Example 1: Standard Production Run

```python
# Standard config (current bash equivalent)
config = PRDConfig(
    memory=MemoryConfig(backend='claude-mem'),
    guardian=GuardianConfig(enabled=True, provider='ollama'),
    context=ContextConfig(strategy='adaptive'),
    workflow=WorkflowConfig(type='8-gen-sequential')
)

orchestrator = get_workflow_orchestrator(config.workflow.type)
result = orchestrator.execute(config)
```

### Example 2: Fast Iteration Mode (No Guardian)

```python
# Disable guardian for fast prototyping
config = PRDConfig.from_yaml('prd-config.yaml')
config.guardian.enabled = False

# Or via environment
# PRD_GUARDIAN_ENABLED=false python -m prd_authoring.main
```

### Example 3: Experiment with New Memory Backend

```python
# Try SQLite backend instead of claude-mem
config = PRDConfig.from_yaml('prd-config.yaml')
config.memory.backend = 'sqlite'
config.memory.fallback_backend = 'claude-mem'  # Fallback if SQLite fails

result = run_prd_generation(config)
metrics.compare(['claude-mem', 'sqlite'])
```

### Example 4: A/B Test Context Strategies

```python
# Run same generation with two strategies
config_a = PRDConfig(context=ContextConfig(strategy='adaptive'))
config_b = PRDConfig(context=ContextConfig(strategy='hybrid'))

result_a = run_prd_generation(config_a)
result_b = run_prd_generation(config_b)

# Compare quality
comparison = compare_results(result_a, result_b)
print(f"Winner: {comparison.winner} (score: {comparison.score_diff})")
```

### Example 5: Swap Workflow Mid-Flight

```python
# Try experimental parallel workflow
config = PRDConfig(workflow=WorkflowConfig(type='15-section-parallel'))

try:
    result = run_prd_generation(config)
except PerformanceIssue:
    # Fallback to sequential
    config.workflow.type = '8-gen-sequential'
    result = run_prd_generation(config)
```

---

## Migration Strategy

### Phase 1: Core Infrastructure (Week 1)

1. **Plugin system**:
   - Create `PluginRegistry`
   - Define all Protocol interfaces
   - Implement bash-wrapper plugins (wraps existing bash)

2. **Configuration**:
   - YAML config loading
   - Environment variable support
   - Config validation

3. **Metrics**:
   - `MetricsCollector`
   - Basic timing and counters

**Deliverable**: Python wrapper around bash implementation with plugin architecture

### Phase 2: First Native Plugins (Week 2)

1. **Memory backends**:
   - Implement `SimpleFileBackend` (no dependencies)
   - Implement `SQLiteMemoryBackend` (better search)
   - Keep `ClaudeMemBackend` as fallback

2. **Context strategies**:
   - Port existing bash logic to Python
   - Implement as separate strategy classes

**Deliverable**: At least 2 native Python implementations per component

### Phase 3: Guardian Plugins (Week 3)

1. **Guardian validators**:
   - Port Ollama guardian to Python
   - Implement `RuleBasedGuardian` (fast, no LLM)
   - Implement `DisabledGuardian`

2. **Workflow orchestrator**:
   - Port 8-generation sequential workflow

**Deliverable**: Complete Python implementation, bash deprecated

### Phase 4: Experimentation (Week 4+)

1. **New implementations**:
   - `HybridContextStrategy` (embeddings-based)
   - `HybridGuardian` (rules + LLM)
   - `Parallel15SectionWorkflow`

2. **A/B testing**:
   - Compare all implementations
   - Measure performance and quality
   - Pick winners

**Deliverable**: Optimized configuration based on data

---

## Directory Structure

```
atomic-claude-python/prd_authoring/
├── __init__.py
├── main.py                      # CLI entry point
├── config.py                    # Configuration dataclasses
├── metrics.py                   # Metrics collection
├── experiments.py               # A/B testing utilities
│
├── plugins/
│   ├── __init__.py              # Plugin registry
│   ├── protocols.py             # All Protocol definitions
│   │
│   ├── memory/
│   │   ├── __init__.py
│   │   ├── claude_mem.py        # Bash wrapper (fallback)
│   │   ├── sqlite_backend.py    # SQLite with FTS5
│   │   ├── simple_file.py       # Simple grep-based
│   │   └── mcp_memory.py        # MCP memory tool (future)
│   │
│   ├── context/
│   │   ├── __init__.py
│   │   ├── full_strategy.py
│   │   ├── structured_strategy.py
│   │   ├── minimal_strategy.py
│   │   ├── adaptive_strategy.py
│   │   └── hybrid_strategy.py   # Embeddings-based (experimental)
│   │
│   ├── guardian/
│   │   ├── __init__.py
│   │   ├── ollama_guardian.py
│   │   ├── disabled_guardian.py
│   │   ├── bedrock_guardian.py
│   │   ├── rule_based_guardian.py
│   │   └── hybrid_guardian.py   # Rules + LLM fallback
│   │
│   └── workflow/
│       ├── __init__.py
│       ├── sequential_8gen.py   # Current approach
│       ├── parallel_15section.py # Experimental
│       └── streaming.py         # Experimental
│
├── orchestrator.py              # PRDOrchestrator (main coordinator)
├── generation.py                # Generation helpers
├── validation.py                # Validation helpers
│
└── tests/
    ├── test_memory_backends.py
    ├── test_context_strategies.py
    ├── test_guardian_validators.py
    └── test_workflows.py
```

---

## Benefits

### 1. Zero Tech Debt

Can swap any component without touching other components:
- Memory backend not working? → Change config, try SQLite
- Guardian too slow? → Disable or use rule-based
- Context overflow? → Switch from adaptive to minimal

### 2. Safe Experimentation

Test new approaches in production without risk:
```python
# Run 10% of PRDs with experimental hybrid guardian
if random.random() < 0.1:
    config.guardian.provider = 'hybrid'
```

### 3. Easy Performance Debugging

Metrics show exactly where time is spent:
```
Generation 1: 120s (90s LLM, 20s memory recall, 10s guardian)
Generation 2: 95s (80s LLM, 5s memory recall, 10s guardian)
...
Bottleneck: Memory recall in Gen 1 (20s)
Solution: Try sqlite backend (5s)
```

### 4. Future-Proof

New backends/strategies can be added without changing existing code:
- Add MCP memory support: Just implement `MCPMemoryBackend`
- Add streaming workflow: Just implement `StreamingWorkflow`
- Add LLM-as-judge guardian: Just implement `LLMJudgeGuardian`

### 5. Testable

Each plugin can be unit tested independently:
```python
def test_sqlite_memory_recall():
    backend = SQLiteMemoryBackend()
    backend.save(1, '106', 'goals', 'User wants speed')
    results = backend.recall(['goals', 'speed'], phase=1)
    assert len(results) == 1
    assert 'speed' in results[0].content
```

---

## Risk Mitigation

### Risk: Plugin system adds complexity

**Mitigation**:
- Start with bash wrappers (zero new complexity)
- Add native plugins incrementally
- Keep config simple (sane defaults)

### Risk: Performance overhead from abstraction

**Mitigation**:
- Protocols have zero runtime cost (duck typing)
- Hot path optimizations where needed
- Metrics show any regressions immediately

### Risk: Too many choices, decision paralysis

**Mitigation**:
- **Default config = current bash behavior**
- Document performance characteristics of each plugin
- A/B testing provides data-driven decisions

---

## Success Criteria

**Week 1**: Plugin system working, can run PRD generation via Python (calling bash)

**Week 2**: At least 1 native Python plugin per component working

**Week 3**: Complete Python implementation, bash deprecated

**Week 4**: Experimental plugins tested, winners selected based on metrics

**Long-term**: Can swap any component via config change with zero code modifications

---

## Summary

**Architecture**: Plugin-based with Protocol interfaces

**Key Benefits**:
- Zero tech debt (swap components anytime)
- Safe experimentation (A/B test in production)
- Performance debugging (metrics show bottlenecks)
- Future-proof (add new implementations easily)

**Migration**: Gradual (bash wrappers → native plugins → experimental plugins)

**Result**: "Build the plane while flying" - can optimize Task 205 based on production data without refactoring

---

**Next Steps**:
1. Review and approve architecture
2. Implement Phase 1 (plugin system + bash wrappers)
3. Run production PRD generation via Python
4. Measure baseline metrics
5. Start adding native plugins incrementally
