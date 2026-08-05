# Releasing

Maintainer-only process to publish a new downloadable version. End users
never run any of this — they just download the zip attached to a GitHub
Release (see the "Download" section in [README.md](README.md)).

1. `powershell -ExecutionPolicy Bypass -File setup\setup_runtime.ps1`
   (re)downloads the embeddable Python runtime and installs pinned
   dependencies into `runtime/` (gitignored, never committed).
2. `powershell -ExecutionPolicy Bypass -File setup\package_app.ps1`
   produces a `.zip` archive containing `runtime/`, `app/`, `run_app.bat`,
   `README.md`, `LICENSE` — everything needed to run, nothing dev-only
   (`.venv/`, `setup/`, `.git/`, `__pycache__/`, `app/logs/`). Deliberately
   `.zip` and not `.7z`: Windows opens `.zip` natively (right-click →
   Extract All), no extra software required for an end user who "n'y
   connaît rien" to GitHub/archives.
3. Bump the version if applicable, commit, tag:
   `git tag v0.1.0 && git push origin v0.1.0`.
4. `gh release create v0.1.0 <archive-path> --title "v0.1.0" --notes "..."`
   (or use the GitHub web UI: Releases → Draft a new release → attach the
   archive as a binary asset).

Do not commit the runtime or the archive into git — attach it as a Release
asset only. A 50-100MB binary committed into git history bloats every
future clone permanently, even if later deleted; a Release asset does not.

No auto-generated desktop shortcut is included in the release archive for
now: a `.lnk` baked at packaging time has an absolute path that would break
once unzipped on the end user's machine. Users just double-click
`run_app.bat` directly, or create their own shortcut to it.

## Pre-publish safety checklist

Re-run before every release, since the source changes between releases:

1. Credential/secret scan (should return nothing outside third-party
   library names):
   ```
   grep -rniE "api[_-]?key|secret|token|password|claude|anthropic|openai|aws_(access|secret)" . --include=*.py --include=*.ps1 --include=*.bat --include=*.md
   ```
2. No hardcoded absolute/user-specific paths in `app/utils/config.py` or
   `app/utils/settings.py` — both should only use `Path(__file__)`-relative
   paths or `QSettings` (which reads/writes to the *end user's* machine at
   runtime, never bakes in a path at build time).
3. `app/logs/` is empty/untracked and excluded from the packaged archive.
4. `.gitignore` still lists `runtime/`, `.venv/`, `__pycache__/`, `*.pyc`,
   `app/logs/`, `*.lnk`, `_scratch_*`.
5. No real sensor/station data is tracked: `git ls-files | grep -iE "\.(parquet|csv|xlsx)$"`
   should return nothing except intentionally-committed sample/test
   fixtures, if any.
