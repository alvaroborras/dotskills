# Advanced Debugging Patterns

Load this file when encountering complex debugging scenarios, performance issues, or when basic patterns aren't sufficient.

## Performance Debugging

### Finding Slow Code Sections

1. Set breakpoints at function boundaries:
   - Start of suspected slow function
   - End of suspected slow function
2. Note timestamps or use `ide_evaluate` to check `time.time()` (Python) or `Date.now()` (JavaScript)
3. Use `ide_step_over` to isolate which lines take time
4. For loops: Use conditional breakpoint `"condition": "i % 1000 == 0"` to sample iterations

### Memory Leak Investigation

1. Set breakpoint at suspected allocation site
2. Use `ide_add_watch` to track object counts: `len(cache)`, `Object.keys(map).length`
3. Step through with `ide_continue_session` to track growth
4. Use `ide_get_variables` to inspect object references

## Concurrent/Async Debugging

### Multi-threaded Race Conditions

1. `ide_get_threads` - Identify all active threads
2. `ide_pause_session` - Pause all threads simultaneously
3. For each thread:
   - `ide_get_stack_trace` with specific `threadId`
   - `ide_get_variables` to check shared state
4. Look for conflicting access to shared resources
5. Use data breakpoints on shared variables if supported

### Async/Promise Chain Debugging

**JavaScript/TypeScript:**
1. Set breakpoints in `.then()` callbacks
2. Use `ide_evaluate` to check promise state: `promise.[[PromiseState]]`
3. Inspect rejection reasons: `promise.[[PromiseResult]]`

**Python async:**
1. Set breakpoints in `async def` functions
2. Use `ide_get_stack_trace` to see async call chain
3. Check coroutine state with `ide_evaluate`: `task.done()`, `task.cancelled()`

## Complex Data Structure Inspection

### Deep Object Navigation

`ide_get_variables` automatically expands nested structures, but for manual exploration:

1. `ide_get_variables` with specific names: `["user"]`
2. Note the `variablesReference` in response
3. `ide_get_scopes` with that reference to dig deeper
4. Or use `ide_evaluate` with dot notation: `user.profile.settings.theme`

### Large Collections

For arrays/lists with hundreds of items:

1. Use conditional breakpoints: `"condition": "items[99] != None"`
2. Evaluate slices: `ide_evaluate` with `items[0:10]` or `items.slice(0, 10)`
3. Check specific indices: `items[suspect_index]`
4. Use watch expressions to track lengths: `ide_add_watch` for `len(items)`

## Exception Handling

### Catching Specific Exceptions

**Language-specific filters:**

Python:
```json
{
  "filters": ["raised", "uncaught"],
  "exceptionOptions": [{
    "path": [{"names": ["ValueError"]}],
    "breakMode": "always"
  }]
}
```

JavaScript:
```json
{
  "filters": ["all", "uncaught"]
}
```

### Exception Analysis

When exception breaks:
1. `ide_get_stack_trace` - See where it originated
2. `ide_get_variables` - Check variable state at throw point
3. Walk up stack with frame-specific evaluation:
   ```json
   {
     "expression": "error_context",
     "frameId": 123
   }
   ```

## State Mutation Tracking

### Finding Where Variable Changes

1. Set data breakpoint with `accessType: "write"` if supported
2. Otherwise: Set regular breakpoints at all assignment locations
3. Use conditional breakpoint: `"condition": "variable != expected_value"`
4. Add watch: `ide_add_watch` for `variable` to track across steps

### Tracking Object Property Changes

1. Set breakpoint before suspected mutation
2. `ide_evaluate` to snapshot: `JSON.stringify(obj)` or `str(obj)`
3. `ide_step_over` to next line
4. Evaluate again and compare
5. For specific properties: `ide_add_watch` with `obj.prop`

## Integration Testing Patterns

### HTTP Request Debugging

1. Set breakpoint in request handler entry point
2. `ide_get_variables` with `["request", "headers", "body"]`
3. Step through validation logic
4. Before response: `ide_evaluate` to inspect `response` object
5. Check status codes: `response.status_code` or `res.statusCode`

### Database Query Debugging

1. Breakpoint before query execution
2. `ide_evaluate` to see query string: `query.as_string()` or `query.toString()`
3. Breakpoint after query
4. Inspect results: `ide_get_variables` with `["results", "rows"]`
5. Check connection state: `connection.is_connected` or similar

## Troubleshooting

### Debug Session Won't Start

1. `ide_list_registrations` - Verify IDE connection
2. Check configuration `type` matches language: `python`, `node`, `lldb`, etc.
3. Verify `program` path is absolute or uses `${file}` variable
4. Ensure no other debug session is active: `ide_list_sessions`, then `ide_terminate_session`

### Breakpoints Not Hitting

1. Verify source URI matches exactly (case-sensitive, absolute path)
2. Check if breakpoint was successfully set: `ide_get_breakpoints`
3. Ensure code actually executes (not in dead code path)
4. For conditional breakpoints: `ide_evaluate` to test condition at suspected location

### Variables Show "Unavailable" or "Optimized Out"

1. Code may be optimized - rebuild with debug flags
2. Variable might be out of scope - check with `ide_get_scopes`
3. Try evaluating expression instead: `ide_evaluate` with variable name
4. Move breakpoint to where variable is definitely in scope

### Frame IDs Invalid

Frame IDs change after any step operation. Always:
1. `ide_get_stack_trace` - Get fresh frame IDs
2. Then use frame ID with `ide_evaluate` or `ide_get_scopes`

### Performance Issues

Multiple tool calls can slow debugging:
- Use `ide_get_variables` with `variableNames` array (80% faster than multiple calls)
- Set multiple breakpoints in single `ide_set_breakpoints` call
- Avoid retrieving all variables when only specific ones are needed

## Language-Specific Tips

### Python

- Use `stopOnEntry: true` to break before any code executes
- Virtual environments: Specify `python` path in configuration
- Django: Use `"django": true` in configuration
- Inspect locals: `ide_evaluate` with `locals().keys()`

### JavaScript/Node.js

- Source maps: Usually handled automatically for TypeScript
- Node modules: Breakpoints work in `node_modules` but may be optimized
- Console output: `ide_get_console` captures `console.log` output
- Inspect global: `ide_evaluate` with `global` (Node) or `window` (browser)

### TypeScript

- Breakpoints use `.ts` source files, not generated `.js`
- If breakpoints don't hit: Check source map configuration
- Type inspection: `ide_evaluate` works with TypeScript types during runtime

### Rust

- Configuration type: `"lldb"` or `"cppdbg"`
- Optimized builds hide variables - use `cargo build` (not `--release`)
- Inspect Option/Result: `ide_evaluate` with `var.is_some()` or pattern matching
- Lifetime issues manifest as use-after-free - watch for moved values

### Go

- Configuration type: `"go"`
- Goroutines appear as threads: `ide_get_threads`
- Channel debugging: `ide_evaluate` with `len(channel)`, `cap(channel)`
- Check goroutine state: Pause and inspect multiple threads

### C/C++

- Configuration type: `"cppdbg"` or `"lldb"`
- Pointer inspection: `ide_evaluate` with `*ptr` or `ptr[index]`
- Memory addresses: Evaluate with `&variable`
- Segfaults: `ide_set_exception_breakpoints` should catch them
