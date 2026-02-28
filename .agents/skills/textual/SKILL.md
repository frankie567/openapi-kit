---
name: textual
description: Provides guidance and reference documentation for building Textual applications. Textual is a Python TUI (terminal user interface) framework. Use this skill when creating, modifying, or debugging Textual apps, widgets, screens, or styles.
compatibility: Requires git and internet access to fetch references.
---

# Textual Skill

Use this skill when working on any code that involves the [Textual](https://github.com/Textualize/textual) Python framework.

## References

Textual documentation is available in the `references/` directory. Always consult it before answering questions about Textual APIs, widgets, events, CSS, or layout.

If the `references/` directory is empty (only contains `.gitkeep`), fetch the docs first by running:

```
.agents/skills/textual/scripts/fetch-references.sh
```

Key reference areas:

- `references/guide/` — Core concepts: app lifecycle, widgets, screens, reactivity, events
- `references/widgets/` — Built-in widget documentation
- `references/styles/` — Textual CSS properties and layout
- `references/api/` — Full API reference

## Instructions

1. Check `references/` for relevant documentation before writing or modifying any Textual code.
2. Run `scripts/fetch-references.sh` if the references are missing.
3. Follow the patterns and conventions shown in the official docs.
4. When in doubt about a widget's API or a CSS property, look it up in `references/` rather than guessing.
