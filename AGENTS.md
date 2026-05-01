# AGENTS.md

Repo-local guidance for `D:\Repos\AnM`.

## Purpose

- Keep AnM as a small, testable Windows-first desktop app for annotating and merging PDFs.
- Prefer maintainable modules over growing one-off script logic.

## Working Rules

- Keep rerun safety intact. Generated PDFs must not be rediscovered as source inputs.
- Preserve both entry points: `python annotate_and_merge.py` and installed command `anm`.
- When changing workflow, build, release, test, or developer setup behavior, actively update this file, `README.md`, and the relevant config or workflow files in the same change.
- When changing CLI behavior, update CLI tests and README examples in the same change.
- Prefer explicit tests for pipeline behavior before adding more UI complexity.
- Keep Windows packaging first-class, but source installs on non-Windows should fail gracefully rather than crash on startup.

## Implementation Notes

- Shared business logic belongs in `src/anm/pipeline.py`; keep Tk-specific code out of it.
- CLI and GUI must share `src/anm/pipeline.py` behavior instead of duplicating PDF processing logic.
- Keep file ordering behavior deterministic and reflected exactly in the GUI list.
- Use repo ignore rules for generated artifacts instead of relying on developers to clean them manually.
- Keep the default GUI output folder derived from included PDFs, while honoring explicit user-selected output folders.
