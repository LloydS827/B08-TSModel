# AGENTS.md

注意：如果设计到生成方案、计划等，请使用中文。

Behavioral guidelines to reduce common LLM coding mistakes. Merge with project-specific instructions as needed.

**Tradeoff:** These guidelines bias toward caution over speed. For trivial tasks, use judgment.

## 1. Think Before Coding

**Don't assume. Don't hide confusion. Surface tradeoffs.**

Before implementing:
- State your assumptions explicitly. If uncertain, ask.
- If multiple interpretations exist, present them - don't pick silently.
- If a simpler approach exists, say so. Push back when warranted.
- If something is unclear, stop. Name what's confusing. Ask.

## 2. Simplicity First

**Minimum code that solves the problem. Nothing speculative.**

- No features beyond what was asked.
- No abstractions for single-use code.
- No "flexibility" or "configurability" that wasn't requested.
- No error handling for impossible scenarios.
- If you write 200 lines and it could be 50, rewrite it.

Ask yourself: "Would a senior engineer say this is overcomplicated?" If yes, simplify.

## 3. Surgical Changes

**Touch only what you must. Clean up only your own mess.**

When editing existing code:
- Don't "improve" adjacent code, comments, or formatting.
- Don't refactor things that aren't broken.
- Match existing style, even if you'd do it differently.
- If you notice unrelated dead code, mention it - don't delete it.

When your changes create orphans:
- Remove imports/variables/functions that YOUR changes made unused.
- Don't remove pre-existing dead code unless asked.

The test: Every changed line should trace directly to the user's request.

## 4. Goal-Driven Execution

**Define success criteria. Loop until verified.**

Transform tasks into verifiable goals:
- "Add validation" → "Write tests for invalid inputs, then make them pass"
- "Fix the bug" → "Write a test that reproduces it, then make it pass"
- "Refactor X" → "Ensure tests pass before and after"

For multi-step tasks, state a brief plan:
```
1. [Step] → verify: [check]
2. [Step] → verify: [check]
3. [Step] → verify: [check]
```

Strong success criteria let you loop independently. Weak criteria ("make it work") require constant clarification.

## 5. Always Keep The System Usable

**The default project state should remain usable for a user who downloads it at any time.**

Treat this like a product invariant, similar to systems such as Codex: even while research and iteration continue, the checked-in default path should be installable, runnable, and verifiable.

When changing the project:
- Do not leave the default branch in a broken, half-migrated, or demo-only state.
- Keep the documented default workflow working unless the task explicitly changes that workflow.
- Preserve existing acceptance paths while adding new ones; do not replace a working baseline with an unproven experiment.
- Keep unfinished or exploratory capabilities behind non-default paths, clear flags, separate docs, or isolated plans.
- After changes, run verification that matches the blast radius, and record any known limitation honestly.
- If a task cannot be completed safely in one pass, leave the system in the last known usable state and document the remaining work.

The test: A new user should be able to read the README, follow the default commands, and get a working local system without needing hidden context from the development discussion.

---

**These guidelines are working if:** fewer unnecessary changes in diffs, fewer rewrites due to overcomplication, and clarifying questions come before implementation rather than after mistakes.
