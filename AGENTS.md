<!-- OPENSPEC:START -->
# OpenSpec Instructions

These instructions are for AI assistants working in this project.

Always open `@/openspec/AGENTS.md` when the request:
- Mentions planning or proposals (words like proposal, spec, change, plan)
- Introduces new capabilities, breaking changes, architecture shifts, or big performance/security work
- Sounds ambiguous and you need the authoritative spec before coding

Use `@/openspec/AGENTS.md` to learn:
- How to create and apply change proposals
- Spec format and conventions
- Project structure and guidelines

Keep this managed block so 'openspec update' can refresh the instructions.

<!-- OPENSPEC:END -->

## Cursor Cloud specific instructions

### Overview
This is a Python Flask web application (ADS-B Line of Sight Calculator) with no database, no build step, and no test suite. All state is in-memory. See `README.md` for full API docs and feature list.

### Running the dev server
```
python3 app.py --debug
```
Binds to `0.0.0.0:5000`. Use `python3` (not `python`) as only `python3` is on PATH by default.

### Gotchas
- The OpenSky Network API (`https://opensky-network.org/api/states/all`) is external and may be rate-limited or unreachable. The app handles this gracefully (returns empty/cached data).
- No automated test suite exists. Validate changes via API calls (`curl`) and/or the web UI at `http://localhost:5000`.
- No linter is configured in the repo. Use standard Python linting tools (e.g. `python3 -m py_compile <file>`) for basic validation.
- Dependencies are in `requirements.txt` (Flask, requests). Install with `pip install -r requirements.txt`.

## Issue Tracking

This project uses **bd (beads)** for issue tracking. Run `bd prime` for workflow context, or install hooks with `bd hooks install` for automatic context injection.

Quick reference:

- `bd ready` - find unblocked work
- `bd create "Title" --type task --priority 2` - create an issue
- `bd close <id>` - close completed work
- `bd dolt push` - push Beads data when using a shared Beads remote

For full workflow details, run `bd prime`.
