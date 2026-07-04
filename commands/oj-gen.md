Help the student write or improve `gen.cpp`, the C++ random data generator.

Arguments: `$ARGUMENTS`

Use the `oj-cpp-rbook-style` skill.

If `gen.cpp` is missing, create the standard template:

```bash
.opencode/oj-tools/bin/oj gen $ARGUMENTS
```

Then adapt `gen.cpp` to the current problem's input format. Keep it small-data by default so `brute.cpp` can verify it.

The generator should:

- print valid input only;
- cover edge cases and random cases;
- keep constraints small enough for brute force;
- use the shared C++ random template style.

Do not generate invalid or overly large stress data unless explicitly asked.
