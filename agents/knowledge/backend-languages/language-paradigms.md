# Programming Language Paradigms Quick Reference

> **Source**: Curated from official language documentation
> **Extracted**: 2025-12-21
> **Refresh**: Annually

## Language Classification Matrix

| Language | Primary Paradigm | Memory | Typing | Concurrency Model |
|----------|------------------|--------|--------|-------------------|
| **Rust** | Systems/Functional | Ownership | Static, Strong | Fearless (ownership) |
| **Go** | Imperative | GC | Static, Strong | Goroutines + Channels |
| **C** | Imperative | Manual | Static, Weak | Threads (pthreads) |
| **C++** | Multi-paradigm | RAII | Static, Strong | Threads + Atomics |
| **Python** | Multi-paradigm | GC | Dynamic, Strong | GIL (asyncio, multiprocessing) |
| **JavaScript** | Multi-paradigm | GC | Dynamic, Weak | Event Loop (async/await) |
| **TypeScript** | Multi-paradigm | GC | Static, Strong | Same as JS |
| **Java** | OOP | GC | Static, Strong | Threads + Virtual Threads |
| **C#** | Multi-paradigm | GC | Static, Strong | async/await + Tasks |
| **Scala** | Functional/OOP | GC (JVM) | Static, Strong | Actors (Akka) |
| **Ruby** | OOP | GC | Dynamic, Strong | Threads + Fibers |
| **PHP** | Multi-paradigm | GC | Dynamic, Weak | Shared-nothing (per-request) |
| **Elixir** | Functional | GC (BEAM) | Dynamic, Strong | Actor Model (OTP) |

## Memory Management Patterns

### Manual (C)
```c
char* buf = malloc(1024);
// ... use buf ...
free(buf);  // Must remember to free
```

### RAII (C++, Rust)
```cpp
{
    std::unique_ptr<Resource> r = make_unique<Resource>();
    // Resource automatically freed when r goes out of scope
}
```

### Ownership (Rust)
```rust
let s1 = String::from("hello");
let s2 = s1;  // s1 is MOVED, no longer valid
// s2 freed when it goes out of scope
```

### Garbage Collection (Java, Python, Go, etc.)
- Reference counting + cycle detection (Python, PHP)
- Tracing GC (Java, Go, .NET)
- BEAM VM (Erlang, Elixir) - per-process heaps

## Concurrency Patterns

### Shared Memory + Locks
**Languages**: C, C++, Java, C#
```java
synchronized(lock) {
    sharedCounter++;
}
```

### Message Passing
**Languages**: Go, Erlang, Elixir
```go
ch := make(chan int)
go func() { ch <- 42 }()
result := <-ch
```

### Actor Model
**Languages**: Erlang, Elixir, Scala (Akka)
```elixir
send(pid, {:message, data})
receive do
  {:message, data} -> handle(data)
end
```

### Async/Await
**Languages**: JavaScript, Python, C#, Rust
```javascript
async function fetch() {
  const response = await fetch(url);
  return await response.json();
}
```

## Type System Comparison

### Static vs Dynamic
- **Static**: Types checked at compile time (Rust, Go, Java, TypeScript)
- **Dynamic**: Types checked at runtime (Python, Ruby, JavaScript)

### Strong vs Weak
- **Strong**: No implicit type coercion (Python: `"3" + 3` → Error)
- **Weak**: Implicit coercion (JavaScript: `"3" + 3` → `"33"`)

### Type Inference
| Language | Inference Level |
|----------|-----------------|
| Rust | Full (Hindley-Milner-like) |
| TypeScript | Partial (flow analysis) |
| Go | Limited (`x := value`) |
| Java | Limited (`var x = value`) |
| Python | None (but type hints) |

## Error Handling Patterns

### Exceptions (Java, Python, C#, Ruby)
```python
try:
    risky_operation()
except SpecificError as e:
    handle(e)
finally:
    cleanup()
```

### Result Types (Rust, Go, Elixir)
```rust
match operation() {
    Ok(value) => use(value),
    Err(e) => handle(e),
}
```

```go
result, err := operation()
if err != nil {
    return err
}
```

### Optional/Maybe (Rust, Scala, Swift)
```rust
match optional_value {
    Some(v) => use(v),
    None => default(),
}
```

## When to Use Which Language

| Use Case | Recommended | Why |
|----------|-------------|-----|
| Systems programming | Rust, C, C++ | Memory control, performance |
| Cloud services | Go, Java, C# | Concurrency, ecosystem |
| Data science/ML | Python | Libraries, ecosystem |
| Web frontend | TypeScript, JavaScript | Browser runtime |
| Web backend | Go, Node.js, Python, Ruby | Developer velocity |
| Enterprise | Java, C# | Stability, tooling |
| Distributed systems | Elixir, Erlang, Go | Fault tolerance |
| Game engines | C++, Rust | Performance |
| Scripting | Python, Ruby, Bash | Readability, speed |

---
*This excerpt was curated for agent knowledge grounding.*
