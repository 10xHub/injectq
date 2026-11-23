# Using InjectQ with AI coding agents

InjectQ ships an [Agent Skill](https://github.com/10xhub/injectq/tree/main/skills/injectq): a short, dense guide written for AI coding agents (Claude Code, Cursor, GitHub Copilot and others). With it loaded, an agent writes idiomatic InjectQ 0.6 code and avoids the traps that raise in 0.6.

## What is in the skill

The folder `skills/injectq/` follows the Agent Skills layout:

| File | Content |
|---|---|
| `SKILL.md` | The recommended app structure, the core API in short snippets, the rules and pitfalls with their fixes, limitations, performance guidance, debugging tools and a checklist. Enough for most tasks. |
| `references/api.md` | Signatures of the public API. |
| `references/integrations.md` | FastAPI, Taskiq and FastMCP setup and per-request behaviour. |
| `references/testing.md` | `override`, `isolated_container`, `container_fixture`, `MockModule`. |
| `references/async-and-concurrency.md` | The ContextVar model, tasks, threads, `aget` rules. |
| `references/migration-0.5-to-0.6.md` | Old and new names, and behaviour changes. |
| `references/performance.md` | Benchmark method and what is fast or slow. |

The agent reads `SKILL.md` first and opens a reference file only when the task needs it.

## Install

### Claude Code

Copy the folder into a skills directory:

```bash
# this project only
mkdir -p .claude/skills && cp -r path/to/injectq/skills/injectq .claude/skills/

# all your projects
mkdir -p ~/.claude/skills && cp -r path/to/injectq/skills/injectq ~/.claude/skills/
```

Claude Code loads the skill when a task involves InjectQ. Commit `.claude/skills/injectq` if you want the whole team to get it.

### Cursor

Add the content of `SKILL.md` as a project rule, for example `.cursor/rules/injectq.mdc` with `alwaysApply: false` and a description such as "Use when writing code that uses the injectq dependency injection library". Add the `references/` files next to it and mention them in the rule, or attach them with `@` when needed.

### GitHub Copilot

Paste `SKILL.md` into `.github/copilot-instructions.md`, or add it as a path-specific file under `.github/instructions/`. Copilot reads one file, so link the reference files by URL.

### Any other agent

Point the agent at the raw file, or paste it into its system prompt, rules or memory:

```text
https://raw.githubusercontent.com/10xhub/injectq/main/skills/injectq/SKILL.md
```

Reference files live next to it, for example
`https://raw.githubusercontent.com/10xhub/injectq/main/skills/injectq/references/testing.md`.

## Keep it current

The skill describes one library version (see the version in `SKILL.md`'s heading). When you upgrade InjectQ, copy the skill from the matching release tag (for example `v0.6.0`, if that tag exists) rather than from `main`:

```text
https://raw.githubusercontent.com/10xhub/injectq/v0.6.0/skills/injectq/SKILL.md
```

If you vendor the folder into your repository, re-copy it when you bump the InjectQ version, and run your tests with `pytest -W error::DeprecationWarning` to catch names the new release deprecates.
