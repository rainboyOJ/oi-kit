Fetch a Luogu problem statement and samples into the rbook-style directory.

Arguments: `$ARGUMENTS`

Use the self-contained helper:

```bash
.opencode/oj-tools/bin/oj fetch $ARGUMENTS
```

Default behavior must preserve student work: existing `problem.md`, samples, code, and notes are skipped unless the user explicitly passes force flags.

After fetching, run:

```bash
.opencode/oj-tools/bin/oj status <problem_dir>
```

Then tell the student what to do next:

1. read `problem.md`;
2. restate the input/output and goal;
3. write or discuss a brute-force idea before asking for the optimized solution.
