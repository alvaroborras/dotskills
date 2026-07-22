# AtCoder Reference

## Contest Types

| Type | ID Pattern | Scoring |
|------|-----------|---------|
| Heuristic | `ahc###` | Higher = better |
| ABC | `abc###` | AC/WA, execution time |
| ARC | `arc###` | AC/WA, execution time |
| AGC | `agc###` | AC/WA, execution time |

## URL Patterns

- Contest: `https://atcoder.jp/contests/{contest}`
- Submissions list: `https://atcoder.jp/contests/{contest}/submissions`
- Single submission: `https://atcoder.jp/contests/{contest}/submissions/{id}`
- Tasks: `https://atcoder.jp/contests/{contest}/tasks`

## Query Parameters for Submissions

| Param | Values | Description |
|-------|--------|-------------|
| `f.Task` | `{contest}_a`, `{contest}_b` | Filter by task |
| `f.Language` | Language ID | Filter by language |
| `f.Status` | `AC`, `WA`, etc. | Filter by status |
| `f.User` | Username | Filter by user |
| `orderBy` | `score`, `created`, `source_length` | Sort field |
| `desc` | `true` | Sort descending |
| `page` | Number | Pagination |

## Language IDs (common)

- 6017: C++23 (GCC 15.2.0)
- 6082: Python (CPython 3.13.7)
- 6088: Rust (rustc 1.89.0)
- 5001: C (GCC 9.2.1)
- 5002: C++14 (GCC 9.2.1)
- 5003: Java (OpenJDK 11.0.6)
- 5004: Python3 (3.8.10)
- 5005: Ruby (2.7.1)
- 5006: C# (.NET Core 3.1)
- 5007: Go (1.14)
- 5008: D (DMD 2.094.2)
- 5009: Swift (5.3.1)
- 5010: Kotlin (1.4.10)
- 5011: Scala (2.13.3)
- 5012: Haskell (GHC 8.10.1)

## HTML Structure for Source Code

```html
<pre id="submission-code" data-ace-mode="c_cpp">
... source code with HTML entities ...
</pre>
```

Decode with: `html.unescape()`

## Rate Limiting

AtCoder uses CloudFront. Be respectful:
- Add 0.5-1s delay between requests
- Don't fetch more than needed
- Cache results locally
