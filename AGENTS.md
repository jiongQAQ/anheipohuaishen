# Repository Guidelines
## Project Structure & Module Organization
The automation suite lives at the repo root. `main.py` hosts the PyQt5 control panel and wires together window, click, account, and logging services. Supporting modules such as `click_sequence.py`, `window_controller.py`, `account_manager.py`, and `process_monitor.py` keep domain logic isolated - extend them rather than embedding helpers in the UI. Configuration defaults sit in `config.json`; operational logs land in `automation.log` and `software_b_runtime.log`. PyInstaller artifacts are regenerated in `build/` and `dist/`, while distributable bundles and Chinese documentation ship under `release_v3/`. Keep disposable experiments outside of these folders so packaged builds stay reproducible.

## Build, Test, and Development Commands
Run the desktop app with `python main.py`. Generate a one-file Windows build via `python build_exe_v3.py`; the script cleans `build/`, `dist/`, and stale `.spec` files before invoking PyInstaller. During troubleshooting, `python coordinate_recorder.py` confirms the Ctrl+3 hotkey pipeline, and `python process_monitor.py` lets you validate process detection without launching the UI. Always activate the virtual environment that provides PyQt5, redis, and pywin32 bindings before running these commands.

## Coding Style & Naming Conventions
Target Python 3.10+ and follow PEP 8: four-space indentation, snake_case for functions, PascalCase for classes, and UPPER_SNAKE_CASE for constants. Keep Qt signal/slot hookups close to their widgets, prefer dependency injection (`update_config`) over globals, and update bilingual docstrings when behaviour changes. New automation steps should land in dedicated helpers under the existing modules to keep `main.py` readable.

## Testing Guidelines
Current automated coverage is lightweight. Execute `python test_concurrent_access.py` against a disposable Redis instance to confirm account locking remains atomic. Record dry runs with the in-app mock-run toggle and inspect `software_b_runtime.log` for regression clues. When adding coordinate-driven flows, store sample coordinates in versioned JSON and document the capture steps in `release_v3/` so other operators can replay them.

## Commit & Pull Request Guidelines
Write imperative, present-tense commit subjects near 60 characters (e.g., `Improve window focus recovery`). In the body, summarise the approach, reference affected modules, and list manual test commands. Pull requests should include: bullet summary of functional changes, test evidence or log excerpts, updated screenshots when UI moves, and any packaging steps maintainers must re-run (typically `python build_exe_v3.py`).
