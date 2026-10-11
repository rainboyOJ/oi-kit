---
description: 分层提示，只给下一步，不给完整正解
argument-hint: "[problem_dir]"
---

Give layered hints for an OJ problem without revealing the full solution.

Arguments: `$ARGUMENTS`

Use the `oj-student-coach` skill. Before giving a hint, check the available context:

```bash
.pi/oj-tools/bin/oj status $ARGUMENTS --json
```

Then read `problem.md` and any existing student notes or code if present.

Hint rules:

1. First clarify what the student has already tried.
2. Give only the next useful hint, not the whole solution.
3. Prefer the chain: brute force -> bottleneck -> observation -> optimization.
4. Ask the student to restate the idea or implement the next small step.
5. Do not write full `main.cpp` in this command.
