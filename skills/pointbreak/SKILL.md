---
name: pointbreak
description: >-
  Guide for using Pointbreak IDE debugger MCP tools to programmatically debug applications.
  TRIGGER when Pointbreak debugger tools are available, especially ide_start_debugging,
  ide_set_breakpoints, ide_continue_session, ide_get_variables, ide_evaluate,
  ide_step_over, ide_step_in, ide_step_out, ide_get_stack_trace, ide_list_sessions,
  or ide_terminate_session. Use when debugging bugs, wrong outputs, crashes, unexpected
  state, or execution-flow questions. Prefer breakpoints and variable inspection over
  print-debugging when runtime behavior is unclear.
---

# Pointbreak Debugging Skill

Use Pointbreak's debugger MCP tools to debug real program execution instead of guessing from static code or adding temporary logging. Set breakpoints, inspect variables, step through execution, and verify runtime state without modifying source files.

## When to Use the Debugger

Use the debugger when:
- A bug depends on runtime state, timing, or control flow
- The user asks why a value is wrong, where a value came from, or what happens at runtime
- A crash or exception is hard to explain from code inspection alone
- You need to verify a hypothesis before changing code

Don't default to the debugger when:
- The bug is obviously explained by static code inspection
- The fix is a trivial typo, missing import, or syntax mistake
- There is no viable launch or attach path for the target process

## Core Debugging Workflow

### 1. Start Debug Session

Launch debugging with `ide_start_debugging`:

```json
{
  "configuration": {
    "type": "python",  // or "node", "lldb", etc.
    "request": "launch",
    "program": "${file}",
    "stopOnEntry": false
  },
  "breakpoints": [{
    "source": {"uri": "file:///path/to/file.py"},
    "breakpoints": [{"line": 42}]
  }]
}
```

Omit `registrationId` - auto-detected. Set initial breakpoints in the same call.

### 2. Set Strategic Breakpoints

Use `ide_set_breakpoints` instead of adding print statements:

```json
{
  "source": {"uri": "file:///path/to/file.py"},
  "breakpoints": [
    {"line": 42},
    {"line": 50, "condition": "x > 0"},
    {"line": 60, "hitCondition": "5"}
  ]
}
```

**Breakpoint types:**
- Basic: Pause at line
- Conditional: `"condition": "x > 0"` - break only when true
- Hit count: `"hitCondition": "5"` - break on Nth hit
- Logpoint: `"logMessage": "Value: {x}"` - print without stopping

**Logpoint caveat:** Expressions evaluate at line start. Variables declared on same line are NOT accessible. Place logpoint on next line or use regular breakpoint + `ide_evaluate`.

### 3. Resume to Breakpoint

Execute with `ide_continue_session` - runs until hitting breakpoint or completion.

### 4. Inspect State

When paused, examine variables with `ide_get_variables`:

**Recommended (80% faster):**
```json
{
  "sessionId": "abc-123",
  "variableNames": ["result", "error", "config"]
}
```

**Alternative (slower):**
```json
{
  "sessionId": "abc-123"
}  // Returns all local variables
```

Auto-selects correct thread/frame, searches scopes (Locals → Globals), expands nested objects.

### 5. Evaluate Expressions

Test hypotheses without code changes using `ide_evaluate`:

```json
{
  "expression": "user_input.strip().lower()",
  "sessionId": "abc-123"
}
```

Examples:
- Variable values: `config.settings.debug`
- Conditionals: `x > 0 && y < 10`
- Function calls: `calculate_total(items)`
- Nested access: `response.data.users[0].email`

### 6. Step Through Execution

Control execution flow:

- `ide_step_over` - Execute current line, pause at next (skip function internals)
- `ide_step_in` - Enter function to trace execution inside
- `ide_step_out` - Run until current function returns

### 7. Understand Call Chain

When execution pauses, use `ide_get_stack_trace` to see how code reached current point:

```json
{
  "threadId": 1,
  "sessionId": "abc-123"
}
```

Returns frames from current location (top) to entry point (bottom). Use frame IDs with `ide_evaluate` or `ide_get_scopes`.

**Critical:** Frame IDs change after stepping. Always call `ide_get_stack_trace` before using `ide_evaluate` or `ide_get_scopes`.

## Common Debugging Patterns

### "Why is this variable wrong?"

1. `ide_set_breakpoints` - Pause where variable is used
2. `ide_continue_session` - Run to breakpoint  
3. `ide_get_variables` with `variableNames` - Check specific values
4. `ide_evaluate` - Test expressions to identify issue

### "What's happening in this loop?"

1. `ide_set_breakpoints` with `condition: "i == 3"` - Break on specific iteration
2. `ide_step_over` - Step through loop body line by line
3. `ide_get_variables` with `variableNames: ["i", "item", "total"]` - Track state changes

### "Where does this value come from?"

1. `ide_set_breakpoints` - Pause where value is wrong
2. `ide_get_stack_trace` - See call chain  
3. `ide_step_out` then `ide_step_over` - Trace through callers
4. `ide_get_variables` - Inspect at each frame

### "When does this exception occur?"

1. `ide_set_exception_breakpoints` - Configure `filters: ["uncaught"]` or `["all"]`
2. `ide_continue_session` - Run until exception
3. `ide_get_stack_trace` - See where it happened
4. `ide_get_variables` - Check state at failure point

## Advanced Features

### Watch Expressions

Track values across steps with `ide_add_watch`:

```json
{
  "expression": "user.balance",
  "sessionId": "abc-123"
}
```

Re-evaluate all watches: `ide_get_watches`

### Data Breakpoints (Watchpoints)

Break when variable is accessed:

1. `ide_get_data_breakpoint_info` - Check if variable supports it
2. `ide_add_data_breakpoint` - Set with `accessType: "write"`, `"read"`, or `"readWrite"`

Requires `supportsDataBreakpoints` capability. Check with `ide_get_capabilities`.

### Console Output

Fetch program output: `ide_get_console` with optional `category: "stdout"`, `"stderr"`, or `"console"`.

### Thread Debugging

Multi-threaded programs:
1. `ide_get_threads` - List all threads
2. `ide_get_stack_trace` - Examine specific thread
3. `ide_pause_session` - Pause running threads

## Session Management

- `ide_list_sessions` - View all active debug sessions
- `ide_terminate_session` - End current or specific session
- Session/registration IDs auto-detected - usually omit these parameters

## Best Practices

**Use breakpoints over print statements.** Inspect on demand without code modification.

**Specify variable names.** `ide_get_variables` with `variableNames` is 80% faster than retrieving all variables.

**Refresh frame IDs after stepping.** Frame IDs invalidate on step operations - call `ide_get_stack_trace` before `ide_evaluate` or `ide_get_scopes`.

**Set initial breakpoints in `ide_start_debugging` when possible.** This avoids missing short-lived programs or tests that finish before later breakpoint calls apply.

**Conditional breakpoints save time.** Instead of breaking every iteration, use `condition: "i >= 100"` to skip to relevant state.

**Check capabilities first.** Use `ide_get_capabilities` before attempting advanced features like data breakpoints or frame restart.

**Logpoints for quick inspection.** When you just need to see values without pausing, use `logMessage: "x={x}, y={y}"` breakpoints.

## Limitations & Fallbacks

**Advanced features:** Not all debug adapters support data breakpoints, frame restart, or step-in targets. Check `ide_get_capabilities` first.

**Custom protocols:** For debug adapter commands not covered by tools, use `ide_send_custom_request` with raw Debug Adapter Protocol commands.

**Multiple IDEs:** If auto-detection fails, use `ide_list_registrations` to find IDE and pass `registrationId` explicitly.

## Quick Reference

| Task | Tool | Key Parameters |
|------|------|----------------|
| Start debugging | `ide_start_debugging` | `configuration`, `breakpoints` |
| Set breakpoints | `ide_set_breakpoints` | `source.uri`, `breakpoints` array |
| Resume execution | `ide_continue_session` | (auto-detected) |
| Inspect variables | `ide_get_variables` | `variableNames` (recommended) |
| Test expression | `ide_evaluate` | `expression` |
| Step over line | `ide_step_over` | (auto-detected) |
| Step into function | `ide_step_in` | (auto-detected) |
| Step out of function | `ide_step_out` | (auto-detected) |
| View call stack | `ide_get_stack_trace` | `threadId` |
| List threads | `ide_get_threads` | (auto-detected) |
| Set exception breaks | `ide_set_exception_breakpoints` | `filters` array |
| Add watch | `ide_add_watch` | `expression` |
| Get console output | `ide_get_console` | `sessionId`, optional `category` |
| End session | `ide_terminate_session` | (auto-detected) |

## Resources

Full tool reference: https://docs.withpointbreak.com/reference/mcp-tools
