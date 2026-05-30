---
name: python-performance-optimization
description: Profile and optimize Python code using cProfile, pyinstrument, memory profilers, and performance best practices. Use when debugging slow Python code, optimizing bottlenecks, or improving application performance.
---

# Python Performance Optimization

Comprehensive guide to profiling, analyzing, and optimizing Python code for better performance, including CPU profiling, pyinstrument sampling profiles, memory optimization, and implementation best practices.

## When to Use This Skill

- Identifying performance bottlenecks in Python applications
- Reducing application latency and response times
- Optimizing CPU-intensive operations
- Reducing memory consumption and memory leaks
- Improving database query performance
- Optimizing I/O operations
- Speeding up data processing pipelines
- Implementing high-performance algorithms
- Profiling production applications

## Core Concepts

### 1. Profiling Types

- **CPU Profiling**: Identify time-consuming functions
- **Memory Profiling**: Track memory allocation and leaks
- **Line Profiling**: Profile at line-by-line granularity
- **Call Graph**: Visualize function call relationships

### 2. Performance Metrics

- **Execution Time**: How long operations take
- **Memory Usage**: Peak and average memory consumption
- **CPU Utilization**: Processor usage patterns
- **I/O Wait**: Time spent on I/O operations

### 3. Optimization Strategies

- **Algorithmic**: Better algorithms and data structures
- **Implementation**: More efficient code patterns
- **Parallelization**: Multi-threading/processing
- **Caching**: Avoid redundant computation
- **Native Extensions**: C/Rust for critical paths

## Quick Start

### Basic Timing

```python
import time

def measure_time():
    """Simple timing measurement."""
    start = time.time()

    # Your code here
    result = sum(range(1000000))

    elapsed = time.time() - start
    print(f"Execution time: {elapsed:.4f} seconds")
    return result

# Better: use timeit for accurate measurements
import timeit

execution_time = timeit.timeit(
    "sum(range(1000000))",
    number=100
)
print(f"Average time: {execution_time/100:.6f} seconds")
```

### Pyinstrument Quick Path

Use `pyinstrument` first when you want a low-friction view of where wall-clock time goes through the full call stack. It is especially useful for request handlers, CLI commands, async code, and exploratory optimization before switching to narrower tools.

```bash
# Install once in the active environment
uv pip install pyinstrument

# Profile a script and inspect a text report in the terminal
pyinstrument script.py

# Save an interactive HTML report
pyinstrument -o profile.html script.py

# Profile an installed CLI entry point
pyinstrument --from-path my-cli --help
```

For targeted blocks, use the Python API:

```python
from pyinstrument import Profiler

profiler = Profiler()
profiler.start()

result = expensive_operation()

profiler.stop()
profiler.print()
profiler.write_html("profile.html")
```

Use a smaller sampling interval only when short-lived code records no samples or misses brief calls. The default interval is `0.001` seconds; lowering it increases overhead. Reach for `py-spy` instead when profiling a live process you cannot instrument directly.

## Detailed patterns and worked examples

Detailed pattern documentation lives in `references/details.md`. Read that file for concrete `pyinstrument`, `cProfile`, line-level, memory, and production-profiling workflows.

If you save several `pyinstrument` sessions as `.pyisession` files, use `scripts/merge_pyinstrument_sessions.py` to combine them into one aggregate report instead of rewriting the `Session.combine()` glue each time.

## Best Practices

1. **Profile before optimizing** - Measure to find real bottlenecks
2. **Focus on hot paths** - Optimize code that runs most frequently
3. **Use appropriate data structures** - Dict for lookups, set for membership
4. **Avoid premature optimization** - Clarity first, then optimize
5. **Use built-in functions** - They're implemented in C
6. **Cache expensive computations** - Use lru_cache
7. **Batch I/O operations** - Reduce system calls
8. **Use generators** for large datasets
9. **Consider NumPy** for numerical operations
10. **Profile production code** - Use py-spy for live systems

## Common Pitfalls

- Optimizing without profiling
- Using global variables unnecessarily
- Not using appropriate data structures
- Creating unnecessary copies of data
- Not using connection pooling for databases
- Ignoring algorithmic complexity
- Over-optimizing rare code paths
- Not considering memory usage
