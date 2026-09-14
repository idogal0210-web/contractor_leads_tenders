---
name: save-and-sync
description: |
  Protocol executed whenever the user says "שמור ועדכן", "שמור וסנכרן", or "Save and update".
  It validates project integrity, enforces zero‑waste directory hygiene, persists files, commits and pushes to GitHub, and produces a structured RTL executive summary.
---

# Save & Sync Protocol ("שמור ועדכן")

> **Purpose**: Provide a deterministic, safe, and idempotent workflow for persisting project state and synchronizing it with a remote GitHub repository. The protocol can run in normal, dry‑run, or test mode.

## Configuration (optional overrides)
- `DRY_RUN=false`  # Set to `true` to simulate actions without modifying the filesystem or remote.
- `RETRY_PUSH=3`   # Number of retry attempts for `git push` on transient failures.
- `MAX_LOG_LINES=200` # Maximum lines to retain in the log artifact.

## Step 1 – Code & Data Integrity Validation
1. **Compilation / Syntax Check** – Run language‑specific compile/check commands (e.g., `python3 -m py_compile **/*.py`, `npm run lint`).
2. **Configuration & Data Validation** – Validate JSON/YAML/TOML files (`json.load`, `yaml.safe_load`).
3. **Import & Dependency Check** – Ensure no broken imports or missing packages.
> **Safety Guard**: Abort immediately on any validation error and report the failing file.

## Step 2 – Zero‑Waste & Lean Directory Hygiene
- **Enforced Rule**: No file may exist in the repository that is not referenced by the build or runtime configuration.
- **Automated Clean‑up** includes:
  - Legacy directories (`legacy/`, `old/`)
  - Duplicate root wrappers
  - Deprecated feature scripts
  - Drafts, temp files (`tmp_*.py`, `sample_*.html`, `*.log`)
  - Cache artefacts (`__pycache__/`, `*.pyc`, `.DS_Store`)
- **Safety Guard** (explicit list of protected paths):
  - `main.py`, any file under `src/`
  - Database files under `data/`
  - Critical configs: `.env`, `requirements.txt`, `.gitignore`
  - Documentation: `README.md`, `docs/`
  - CI/CD pipelines: `.github/workflows/`
- **Dry‑Run Mode** lists files that *would* be removed without deleting them.

## Step 3 – Local Persistence & Build
1. **Persist Changes** – Ensure all edited/created files are flushed to disk.
2. **Run Build Scripts** – Execute project‑specific build commands if present (`make`, `npm run build`, `cargo build`).
3. **Validate .gitignore** – Confirm it excludes generated files and secrets.

## Step 4 – GitHub Synchronisation
> **All Git operations assume GitHub as the remote.**
1. **Detect Current Branch** – `git rev-parse --abbrev-ref HEAD`. Abort if in detached HEAD.
2. **Stage All Changes** – `git add -A` (skip if `DRY_RUN`).
3. **Generate Semantic Commit Message** –
   - If there are only deletions: `chore(clean): remove unused files`
   - If there are additions/updates: `feat(sync): update project assets`
   - Include a short summary of changed modules (auto‑generated).
4. **Commit** – `git commit -m "<generated message>"` (skip if no changes).
5. **Push with Retries** – Attempt `git push origin <branch>` up to `RETRY_PUSH` times, backing off exponentially.
6. **Post‑Push Verification** – Ensure `git status --porcelain` is clean.
7. **Optional Remote Validation** – Run `git ls-remote --exit-code origin <branch>` to confirm remote acceptance.

## Step 5 – RTL Executive Summary (HTML fragment)
```html
<div dir="rtl" style="text-align: right; font-family: system-ui, sans-serif;">
  <h3>✅ סיכום ביצוע</h3>
  <ul>
    <li>🔧 <strong>בדיקת תקינות:</strong> <span id="integrity-status">✅</span></li>
    <li>🧹 <strong>טיהור קבצים מיותרים:</strong> <span id="cleanup-count">0 קבצים</span></li>
    <li>📂 <strong>קבצים נשמרו:</strong> <span id="saved-files-count">0 קבצים</span></li>
    <li>🚀 <strong>סינכרון GitHub:</strong> <span id="git-status">✅ דחיפה הצליחה</span></li>
    <li>🔗 <strong>Commit Hash:</strong> <code id="commit-hash">N/A</code></li>
  </ul>
  <p>הפרויקט רזה, נקי, ומסונכרן במלואו.</p>
</div>
```
The UI layer that renders the skill should inject the above HTML into the chat output.

## Logging & Auditing
- All steps write to `logs/save-and-sync.log` (rotated daily, keep last `MAX_LOG_LINES`).
- In `DRY_RUN` mode, actions are logged with the prefix `[DRY‑RUN]`.
- Errors are returned with a JSON payload `{"error": "<msg>", "step": <number>}` for downstream handling.

## Idempotence Guarantees
- Re‑running the skill on a clean working tree results in a no‑op commit (`git commit` will skip if no changes).
- Cleanup only removes files that match the explicit patterns and are not in the safety‑guard list.
- Push retries do not create duplicate commits.

---
*This skill is designed for Antigravity 2.0+ and follows the Conventional Commits specification.*
