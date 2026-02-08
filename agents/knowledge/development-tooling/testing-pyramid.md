# Testing Pyramid and Best Practices

> **Sources**:
> - https://martinfowler.com/bliki/TestPyramid.html
> - https://kentbeck.github.io/TestDesiderata/
> - https://stryker-mutator.io/docs/
> **Extracted**: 2025-12-21
> **Refresh**: Annually (stable concepts)

## The Testing Pyramid

```
        /\
       /  \     E2E Tests (Few)
      /----\    - Slow, expensive, brittle
     /      \   - Test critical user journeys
    /--------\  Integration Tests (Some)
   /          \ - Test component interactions
  /------------\ - Database, API, external services
 /              \ Unit Tests (Many)
/----------------\ - Fast, isolated, focused
                   - Test business logic
```

## Test Categories

### Unit Tests (Base of Pyramid)
**Characteristics**:
- Fast (milliseconds)
- Isolated (no external dependencies)
- Deterministic (same result every time)
- Focus on single unit of behavior

**Best Practices**:
- One assertion concept per test
- Descriptive test names (should_do_X_when_Y)
- Arrange-Act-Assert pattern
- Test behavior, not implementation

### Integration Tests (Middle)
**Characteristics**:
- Test component boundaries
- May use real databases (via testcontainers)
- Verify API contracts
- Test error handling across systems

**Best Practices**:
- Use contract testing (Pact) for APIs
- Prefer testcontainers over mocks for databases
- Test happy path + key error scenarios
- Keep setup/teardown clean

### End-to-End Tests (Top)
**Characteristics**:
- Test full user journeys
- Slowest and most expensive
- Most prone to flakiness
- Highest confidence when passing

**Best Practices**:
- Limit to critical business flows
- Use page object pattern
- Implement retry logic for flaky elements
- Run in isolated environments

## Kent Beck's Test Desiderata

Properties that make tests valuable:

| Property | Description |
|----------|-------------|
| **Isolated** | Tests don't affect each other |
| **Composable** | Can run any subset of tests |
| **Fast** | Quick feedback loop |
| **Inspiring** | Passing tests give confidence |
| **Writable** | Easy to write new tests |
| **Readable** | Tests serve as documentation |
| **Behavioral** | Test behavior, not implementation |
| **Structure-insensitive** | Refactoring doesn't break tests |
| **Automated** | No manual steps required |
| **Specific** | Failures point to exact problem |
| **Deterministic** | Same result every run |
| **Predictive** | Passing means production will work |

## Mutation Testing

**Concept**: Inject faults (mutants) into code, verify tests catch them

**Common Mutators**:
- Arithmetic: `+` → `-`, `*` → `/`
- Conditional: `>` → `>=`, `==` → `!=`
- Boolean: `true` → `false`, `&&` → `||`
- Return values: `return x` → `return null`

**Mutation Score**:
```
Score = (Killed Mutants / Total Mutants) × 100%
```

**Tools by Language**:
| Language | Tool |
|----------|------|
| JavaScript/TypeScript | Stryker |
| Java | PIT (pitest) |
| Python | mutmut |
| Rust | cargo-mutants |
| C# | Stryker.NET |

**Target**: 80%+ mutation score for critical code

## Test Coverage Guidelines

| Coverage Type | Target | Notes |
|---------------|--------|-------|
| Line Coverage | 80%+ | Basic metric |
| Branch Coverage | 70%+ | More meaningful |
| Mutation Score | 80%+ | Best indicator of test quality |

**Warning**: High coverage ≠ good tests. Mutation testing reveals test quality.

## Anti-Patterns to Avoid

1. **Ice Cream Cone** - Too many E2E, too few unit tests
2. **Testing Implementation** - Tests break on refactor
3. **Flaky Tests** - Non-deterministic results
4. **Slow Tests** - Discourages running tests
5. **Test Interdependence** - Tests must run in order
6. **Excessive Mocking** - Tests pass but code fails
7. **No Assertions** - Tests that can't fail

---
*This excerpt was curated for agent knowledge grounding. See source URLs for full context.*
