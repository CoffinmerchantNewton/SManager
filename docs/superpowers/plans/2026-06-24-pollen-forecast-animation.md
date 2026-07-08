# Pollen Forecast Animation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a smooth five-region, seven-day pollen forecast animation and restore the server postprocess product path.

**Architecture:** Keep forecast computation intact. Attach an idempotent postprocess export after successful WRF output movement, expose existing products through the local backend, and make the public Portal choose regions and bundles explicitly.

**Tech Stack:** Python postprocessing, Slurm shell scripts, FastAPI product proxy, React/Vite/Cesium frontend, Docker Compose.

---

### Task 1: Protect Local Companion Artifacts

**Files:**
- Modify: `.gitignore`

- [x] Add `.superpowers/` to `.gitignore`.

### Task 2: Restore Server Product Generation

**Files:**
- Modify: `auto-pollen-lijt/scripts/auto_pollen_forecast.py`
- Modify: server `/g7/anxq/Zhangjt/workspace/auto-pollen-lijt/scripts/auto_pollen_forecast.py`

- [ ] Find the generated `run.sbatch` template.
- [ ] Write a failing text-level regression test or script assertion that generated `run.sbatch` contains `postprocess_forecast.py`.
- [ ] Add a postprocess block immediately after `mark-wrf-success`.
- [ ] Keep the block post-WRF only and do not alter prep/FNL/WRF logic.
- [ ] Deploy the same change to the server.

### Task 3: Backfill Existing Completed Runs

**Files:**
- Server runtime outputs only.

- [ ] Run `postprocess_forecast.py --products-only` for completed `spring/beijing/2026/0624`.
- [ ] Run it for completed `spring/china/2026/0624`.
- [ ] Verify product manifest, map forecast, city forecast, and postprocess state exist.
- [ ] Leave failed/running regions untouched except reporting status.

### Task 4: Make Portal Region-First

**Files:**
- Modify: `frontend/src/pages/Portal.tsx`
- Modify: `frontend/src/types/index.ts` if needed.
- Modify: `frontend/src/i18n.tsx`

- [ ] Extract bundle discovery and frame/timeline helpers into testable pure functions if needed.
- [ ] Write failing tests for region filtering and latest-bundle selection if a test runner is available.
- [ ] Add five region tabs.
- [ ] Load latest products per region, preferring server-backed bundles.
- [ ] Preload or normalize map frames before playback starts.
- [ ] Keep playback controls simple: previous, play/pause, next, seven day scrubber.

### Task 5: Verify And Deploy

**Files:**
- Local Docker Compose deployment.
- Server `screen -r smanager` service.

- [ ] Run frontend build.
- [ ] Run backend import or targeted API smoke checks.
- [ ] Rebuild/restart local Docker services.
- [ ] Restart or refresh the server `smanager` service if code changed under the daemon.
- [ ] Verify local frontend can load a generated server product bundle.
