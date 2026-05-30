# python-performance-optimization — detailed patterns and worked examples

## Profiling Tools

### Pattern 1: cProfile - CPU Profiling

```python
import cProfile
import pstats
from pstats import SortKey

def slow_function():
    """Function to profile."""
    total = 0
    for i in range(1000000):
        total += i
    return total

def another_function():
    """Another function."""
    return [i**2 for i in range(100000)]

def main():
    """Main function to profile."""
    result1 = slow_function()
    result2 = another_function()
    return result1, result2

# Profile the code
if __name__ == "__main__":
    profiler = cProfile.Profile()
    profiler.enable()

    main()

    profiler.disable()

    # Print stats
    stats = pstats.Stats(profiler)
    stats.sort_stats(SortKey.CUMULATIVE)
    stats.print_stats(10)  # Top 10 functions

    # Save to file for later analysis
    stats.dump_stats("profile_output.prof")
```

**Command-line profiling:**

```bash
# Profile a script
python -m cProfile -o output.prof script.py

# View results
python -m pstats output.prof
# In pstats:
# sort cumtime
# stats 10
```

### Pattern 2: pyinstrument - Sampling Call-Stack Profiling

Use `pyinstrument` when you want a fast, readable picture of wall-clock time across the call stack without instrumenting every function. It is usually the best first profiler for interactive diagnosis.

**Install with uv:**

```bash
uv pip install pyinstrument
```

**Profile a script:**

```bash
# Text report in the terminal
pyinstrument script.py

# Save an interactive HTML report
pyinstrument -o profile.html script.py

# Save a reusable session for later rendering or merging
pyinstrument -o profile.pyisession script.py

# Render as percentages of total time
pyinstrument -p time=percent_of_total script.py

# Use timeline mode to preserve call order
pyinstrument -t script.py
```

**Profile a module or installed CLI command:**

```bash
# Equivalent to python -m package.module
pyinstrument -m package.module

# Profile an installed console script from PATH
pyinstrument --from-path my-cli arg1 arg2
```

**Load a saved session or export to other viewers:**

```bash
# Re-open a saved session in terminal output
pyinstrument --load profile.pyisession

# Write a flamechart-compatible file for https://www.speedscope.app/
pyinstrument -o profile.speedscope.json script.py

# Profile inline code without a separate file
pyinstrument -c "from myapp import run; run()"
```

**Profile a specific code block:**

```python
from pyinstrument import Profiler

def build_report(records):
    """Profile a specific hot path."""
    profiler = Profiler()
    profiler.start()

    summary = {}
    for record in records:
        summary[record.user_id] = transform(record)

    profiler.stop()
    profiler.print()
    profiler.write_html("profile.html")
    return summary
```

**Use the context-manager helper for short experiments:**

```python
import pyinstrument

with pyinstrument.profile():
    run_batch_job()
```

**Profile async code explicitly:**

```python
import asyncio
from pyinstrument import Profiler

async def main():
    profiler = Profiler(async_mode="enabled")
    with profiler:
        await run_async_pipeline()
    profiler.print()

asyncio.run(main())
```

**Profile IPython or Jupyter cells:**

```python
%load_ext pyinstrument

%%pyinstrument
run_notebook_cell()
```

**Profile pytest:**

```bash
# One aggregate report for a test run
pyinstrument -m pytest tests/test_api.py -k hot_path
```

```python
from pathlib import Path

import pytest
from pyinstrument import Profiler

TESTS_ROOT = Path.cwd()


@pytest.fixture(autouse=True)
def auto_profile(request):
    profile_root = TESTS_ROOT / ".profiles"
    profiler = Profiler()
    profiler.start()

    yield

    session = profiler.stop()
    profile_root.mkdir(exist_ok=True)
    session.save(profile_root / f"{request.node.name}.pyisession")
```

After collecting per-test sessions, merge them with the bundled script:

```bash
uv run --with pyinstrument \
  skills/python-performance-optimization/scripts/merge_pyinstrument_sessions.py \
  .profiles/test_a.pyisession \
  .profiles/test_b.pyisession \
  -o .profiles/combined.html
```

**Profile web requests:**

- Django: add `pyinstrument.middleware.ProfilerMiddleware`, then use `?profile` for one request or `PYINSTRUMENT_PROFILE_DIR = "profiles"` to capture HTML for all requests in development.
- Flask or FastAPI: wrap the request in middleware, start a `Profiler()` before the handler, stop it after the response, and return `profiler.output_html()` when profiling is enabled.
- Aiohttp/Litestar: the official docs show the same middleware pattern with `Profiler()` around each request.

**Interpretation notes:**

- Prefer the HTML report when the call tree is deep or you need to collapse library frames interactively.
- Prefer text output for quick iteration in the terminal.
- Save `.pyisession` when you expect to re-render, diff, or merge profiles later.
- Use the default sampling interval (`0.001`) first; lower it only if short-lived work disappears from the report, because smaller intervals add overhead and memory use.
- Use `--show-all` only when hidden library frames are likely to matter. Most of the time the default filtered view is easier to read.
- Reach for `-p processor_options.filter_threshold=0` when pyinstrument collapses small frames that you still need to inspect.
- Use `--target-description` when you want reports labeled with stable task names instead of the full raw command line.
- Use `pyinstrument` for code you can run directly. Use `py-spy` instead for live or externally managed processes.

**Known issues and caveats:**

- Pyinstrument is a statistical wall-clock profiler, not a per-call tracer. Use `cProfile` or `line_profiler` when you need deterministic per-call or per-line accounting.
- The project documents that profiling inside Docker can produce odd results because the timing syscall can be slow there. Validate suspicious traces outside the container when possible.
- The project also notes that `pyinstrument script.py` can misbehave when the script relies on classes pickled from `__main__`. Prefer profiling the module entry point with `-m` when that applies.

### Pattern 3: line_profiler - Line-by-Line Profiling

```python
# Install: pip install line-profiler

# Add @profile decorator (line_profiler provides this)
@profile
def process_data(data):
    """Process data with line profiling."""
    result = []
    for item in data:
        processed = item * 2
        result.append(processed)
    return result

# Run with:
# kernprof -l -v script.py
```

**Manual line profiling:**

```python
from line_profiler import LineProfiler

def process_data(data):
    """Function to profile."""
    result = []
    for item in data:
        processed = item * 2
        result.append(processed)
    return result

if __name__ == "__main__":
    lp = LineProfiler()
    lp.add_function(process_data)

    data = list(range(100000))

    lp_wrapper = lp(process_data)
    lp_wrapper(data)

    lp.print_stats()
```

### Pattern 4: memory_profiler - Memory Usage

```python
# Install: pip install memory-profiler

from memory_profiler import profile

@profile
def memory_intensive():
    """Function that uses lots of memory."""
    # Create large list
    big_list = [i for i in range(1000000)]

    # Create large dict
    big_dict = {i: i**2 for i in range(100000)}

    # Process data
    result = sum(big_list)

    return result

if __name__ == "__main__":
    memory_intensive()

# Run with:
# python -m memory_profiler script.py
```

### Pattern 5: py-spy - Production Profiling

```bash
# Install: pip install py-spy

# Profile a running Python process
py-spy top --pid 12345

# Generate flamegraph
py-spy record -o profile.svg --pid 12345

# Profile a script
py-spy record -o profile.svg -- python script.py

# Dump current call stack
py-spy dump --pid 12345
```

## Optimization Patterns

### Pattern 6: List Comprehensions vs Loops

```python
import timeit

# Slow: Traditional loop
def slow_squares(n):
    """Create list of squares using loop."""
    result = []
    for i in range(n):
        result.append(i**2)
    return result

# Fast: List comprehension
def fast_squares(n):
    """Create list of squares using comprehension."""
    return [i**2 for i in range(n)]

# Benchmark
n = 100000

slow_time = timeit.timeit(lambda: slow_squares(n), number=100)
fast_time = timeit.timeit(lambda: fast_squares(n), number=100)

print(f"Loop: {slow_time:.4f}s")
print(f"Comprehension: {fast_time:.4f}s")
print(f"Speedup: {slow_time/fast_time:.2f}x")

# Even faster for simple operations: map
def faster_squares(n):
    """Use map for even better performance."""
    return list(map(lambda x: x**2, range(n)))
```

### Pattern 7: Generator Expressions for Memory

```python
import sys

def list_approach():
    """Memory-intensive list."""
    data = [i**2 for i in range(1000000)]
    return sum(data)

def generator_approach():
    """Memory-efficient generator."""
    data = (i**2 for i in range(1000000))
    return sum(data)

# Memory comparison
list_data = [i for i in range(1000000)]
gen_data = (i for i in range(1000000))

print(f"List size: {sys.getsizeof(list_data)} bytes")
print(f"Generator size: {sys.getsizeof(gen_data)} bytes")

# Generators use constant memory regardless of size
```

### Pattern 8: String Concatenation

```python
import timeit

def slow_concat(items):
    """Slow string concatenation."""
    result = ""
    for item in items:
        result += str(item)
    return result

def fast_concat(items):
    """Fast string concatenation with join."""
    return "".join(str(item) for item in items)

def faster_concat(items):
    """Even faster with list."""
    parts = [str(item) for item in items]
    return "".join(parts)

items = list(range(10000))

# Benchmark
slow = timeit.timeit(lambda: slow_concat(items), number=100)
fast = timeit.timeit(lambda: fast_concat(items), number=100)
faster = timeit.timeit(lambda: faster_concat(items), number=100)

print(f"Concatenation (+): {slow:.4f}s")
print(f"Join (generator): {fast:.4f}s")
print(f"Join (list): {faster:.4f}s")
```

### Pattern 9: Dictionary Lookups vs List Searches

```python
import timeit

# Create test data
size = 10000
items = list(range(size))
lookup_dict = {i: i for i in range(size)}

def list_search(items, target):
    """O(n) search in list."""
    return target in items

def dict_search(lookup_dict, target):
    """O(1) search in dict."""
    return target in lookup_dict

target = size - 1  # Worst case for list

# Benchmark
list_time = timeit.timeit(
    lambda: list_search(items, target),
    number=1000
)
dict_time = timeit.timeit(
    lambda: dict_search(lookup_dict, target),
    number=1000
)

print(f"List search: {list_time:.6f}s")
print(f"Dict search: {dict_time:.6f}s")
print(f"Speedup: {list_time/dict_time:.0f}x")
```

### Pattern 9: Local Variable Access

```python
import timeit

# Global variable (slow)
GLOBAL_VALUE = 100

def use_global():
    """Access global variable."""
    total = 0
    for i in range(10000):
        total += GLOBAL_VALUE
    return total

def use_local():
    """Use local variable."""
    local_value = 100
    total = 0
    for i in range(10000):
        total += local_value
    return total

# Local is faster
global_time = timeit.timeit(use_global, number=1000)
local_time = timeit.timeit(use_local, number=1000)

print(f"Global access: {global_time:.4f}s")
print(f"Local access: {local_time:.4f}s")
print(f"Speedup: {global_time/local_time:.2f}x")
```

### Pattern 10: Function Call Overhead

```python
import timeit

def calculate_inline():
    """Inline calculation."""
    total = 0
    for i in range(10000):
        total += i * 2 + 1
    return total

def helper_function(x):
    """Helper function."""
    return x * 2 + 1

def calculate_with_function():
    """Calculation with function calls."""
    total = 0
    for i in range(10000):
        total += helper_function(i)
    return total

# Inline is faster due to no call overhead
inline_time = timeit.timeit(calculate_inline, number=1000)
function_time = timeit.timeit(calculate_with_function, number=1000)

print(f"Inline: {inline_time:.4f}s")
print(f"Function calls: {function_time:.4f}s")
```

For advanced optimization techniques including NumPy vectorization, caching, memory management, parallelization, async I/O, database optimization, and benchmarking tools, see [references/advanced-patterns.md](references/advanced-patterns.md)
