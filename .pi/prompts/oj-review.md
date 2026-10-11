---
description: 审查学生已写的 main.cpp，给针对性修复
argument-hint: "[problem_dir]"
---

Review the student's existing solution code.

Arguments: `$ARGUMENTS`

Use the `oj-student-coach` and `oj-cpp-rbook-style` skills.

Read `problem.md`, `main.cpp`, and any failing sample or `duipai-failed/failed.in` if present.

Review priority:

1. correctness bugs;
2. boundary cases;
3. complexity mismatch with constraints;
4. implementation risks;
5. style/readability issues.

Do not rewrite the entire optimized solution by default. Give targeted fixes and ask the student to patch the code. If a small patch is clearly needed, explain it before editing.
