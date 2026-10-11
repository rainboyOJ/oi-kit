---
description: 查看当前题目的学习流程状态（oj status）
argument-hint: "[problem_dir]"
---

Check the current OJ problem workflow status.

Arguments: `$ARGUMENTS`

Run:

```bash
.pi/oj-tools/bin/oj status $ARGUMENTS
```

Explain the result in Chinese. Focus on the next concrete student action:

- missing problem statement or samples;
- missing `main.cpp`;
- missing `brute.cpp`;
- missing `gen.cpp`;
- whether `oj sample` or `oj duipai` is ready.

Do not solve the problem from scratch in this command.
