Run stress testing for `main.cpp` against `brute.cpp` using `gen.cpp`.

Arguments: `$ARGUMENTS`

Run:

```bash
.opencode/oj-tools/bin/oj duipai $ARGUMENTS
```

The expected three-file workflow is:

- `main.cpp`: student's optimized solution;
- `brute.cpp`: small-data brute-force solution;
- `gen.cpp`: C++ random data generator.

If any file is missing, explain which learning step is missing. If a counterexample is found, inspect `duipai-failed/failed.in`, `user.out`, and `brute.out`, then guide the student to locate the bug. Prefer asking targeted questions over rewriting the full solution.
