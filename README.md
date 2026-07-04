# OpenCode OJ Student Toolkit

This directory is self-contained and can be moved to another rbook-style project.

## CLI

Use:

```bash
.opencode/oj-tools/bin/oj new luogu P1001
.opencode/oj-tools/bin/oj fetch P1001
.opencode/oj-tools/bin/oj status
.opencode/oj-tools/bin/oj run
.opencode/oj-tools/bin/oj sample
.opencode/oj-tools/bin/oj duipai 100
```

The expected problem structure is:

```text
problems/<oj>/<problem_id>/
  problem.md
  index.md
  main.cpp
  brute.cpp
  gen.cpp
  in / out / in1 / out1
```

## OpenCode Commands

Commands are in `.opencode/commands/`:

```text
/oj-new
/oj-fetch
/oj-status
/oj-hint
/oj-brute
/oj-gen
/oj-run
/oj-sample
/oj-duipai
/oj-review
/oj-reference
```

The learning policy is: problem understanding first, brute force second, optimized solution later.
