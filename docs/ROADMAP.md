# Roadmap

## Current phase — installer and hidden activation (alpha 2)

- Existing prototype and initial GitHub push are the baseline; continue that code.
- Build a `.deb` containing the model and private native runtime, with standard dependencies managed by APT.
- Explicit activation hides Orbit; Hey Orbit reveals it.
- Persist activation and optional login startup; reopen a single instance from the menu.
- Test the installer payload, then complete privileged installation and real login/microphone QA.
- Review and commit this phase before its push. No automatic GitHub Release publication.
- See `docs/PHASE_INSTALLER_FA.md` for this phase's learning path and acceptance checks.

## Learning milestone 1 — understand and run the foundation

- Python interpreter, virtual environment, modules, functions, dataclasses.
- Understand `core.py` through short exercises.
- Run the tests and doctor report.
- Open the GTK development window and launch one chosen app.
- Review the repository before the first GitHub push.

## Learning milestone 2 — COSMIC island and English voice

- Build/package Layer Shell and validate positioning and keyboard focus.
- Install the model and test a real microphone.
- Type and speak the same command through the same catalog.
- Measure wake false activations and command latency; keep an engine decision log.
- Polish expansion/collapse animation and error states.

## Learning milestone 3 — a useful Programming routine

- Select application steps from a GUI.
- Add a project directory to editor and terminal actions.
- Add explicit PostgreSQL service actions with readiness and authorization.
- Add routine edit/delete, cancellation, and resilient startup handling.

## First public v1 — voice and typing together

- A polished, measured COSMIC/Wayland experience; English UI and voice.
- A tested keyboard shortcut or desktop shortcut fallback.
- Reproducible `.deb` packaging, model onboarding, microphone selection.
- Installation tested on a clean Pop!_OS machine.
- Clear compatibility matrix, demo, contribution instructions, and release notes.
- Do not mark v1 ready while speech, focus handling, or installation QA is pending.

## Subsequent versions — Ubuntu/GNOME

- Test the engine and normal window on selected Ubuntu/GNOME versions.
- Design and implement the GNOME Shell presentation adapter.
- Test GNOME version compatibility and Wayland permissions explicitly.
- Share voice, catalog, action types, and routines across presentation backends.
- Investigate app-content search only through explicit integrations.
