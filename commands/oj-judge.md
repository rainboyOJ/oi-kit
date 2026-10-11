Judge `main.cpp` against the problem's test data with real memory accounting.

Arguments: `$ARGUMENTS`

Run:

```bash
.opencode/oj-tools/bin/oj judge $ARGUMENTS
```

This delegates to `roj-local-judge-lite` (installed separately). Unlike `oj sample`, it
runs the submission under a cgroup, so it can report **MLE** and compare CPU time in
microseconds. Use it for final acceptance, not for quick iteration — `oj run` and
`oj sample` are lighter and need no cgroup.

Read the verdict like this:

- `AC` / `WA` — answer correct or first differing line (the `message` field carries it)
- `TLE` / `MLE` / `RE` — decisive execution outcome; `MLE` only appears with cgroup
- `SE` — infrastructure fault (executor missing, cgroup unavailable). **Not the
  submission's fault**; check the message for a path, and see the troubleshooting
  section of the judge's own skill.
- `CE` — compilation failed; the compiler output is in `compile.output`

If the output mentions `isolation: degraded`, memory was not measured and MLE is
unavailable — say so rather than treating "no MLE" as "memory is fine".

If `oj judge` reports it cannot find `judge.py`, tell the student how to install
`roj-local-judge-lite` (see README) instead of falling back silently — and note that
`oj sample` still works without it.

When the result is WA, prefer asking targeted questions about the failing case over
rewriting the solution.
