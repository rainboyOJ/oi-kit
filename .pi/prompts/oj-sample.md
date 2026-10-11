---
description: 编译 main.cpp 并跑题目全部样例（oj sample）
argument-hint: "[problem_dir]"
---

Compile `main.cpp` and run all samples / local data for the current problem.

Arguments: `$ARGUMENTS`

Run:

```bash
.pi/oj-tools/bin/oj sample $ARGUMENTS
```

If a case fails, summarize:

- which case failed;
- whether it is compile error, runtime error, timeout, or wrong answer;
- the smallest useful difference between expected and actual output;
- one suggested debugging direction.

Do not immediately provide a full corrected solution. Ask the student to inspect the failing case first.
