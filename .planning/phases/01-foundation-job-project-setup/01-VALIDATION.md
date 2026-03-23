---
phase: 1
slug: foundation-job-project-setup
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-23
---

# Phase 1 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.x + pytest-asyncio |
| **Config file** | `pyproject.toml` — Wave 0 installs |
| **Quick run command** | `uv run pytest tests/ -x -q` |
| **Full suite command** | `uv run pytest tests/ -v` |
| **Estimated runtime** | ~5 seconds |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/ -x -q`
- **After every plan wave:** Run `uv run pytest tests/ -v`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 10 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 1-01-01 | 01 | 0 | JOB-01 | unit | `uv run pytest tests/test_models.py -x -q` | ❌ W0 | ⬜ pending |
| 1-01-02 | 01 | 0 | JOB-02 | unit | `uv run pytest tests/test_models.py::test_job_search_scope -x -q` | ❌ W0 | ⬜ pending |
| 1-01-03 | 01 | 0 | JOB-03 | unit | `uv run pytest tests/test_models.py::test_job_status_lifecycle -x -q` | ❌ W0 | ⬜ pending |
| 1-02-01 | 02 | 1 | JOB-04 | integration | `uv run pytest tests/test_routes.py::test_job_list_dashboard -x -q` | ❌ W0 | ⬜ pending |
| 1-02-02 | 02 | 1 | JOB-04 | integration | `uv run pytest tests/test_routes.py::test_create_job_form -x -q` | ❌ W0 | ⬜ pending |
| 1-02-03 | 02 | 1 | JOB-04 | integration | `uv run pytest tests/test_routes.py::test_archive_job -x -q` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/__init__.py` — package marker
- [ ] `tests/conftest.py` — in-memory SQLite session fixture
- [ ] `tests/test_models.py` — stubs for JOB-01, JOB-02, JOB-03
- [ ] `tests/test_routes.py` — stubs for JOB-04 route tests
- [ ] `pyproject.toml` with `[tool.pytest.ini_options]` and `pytest-asyncio` in dev deps

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Job list dashboard renders correctly in browser | JOB-04 | Visual rendering requires human review | Start server `uv run uvicorn app.main:app`, navigate to `/jobs`, verify list displays with status badges |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 10s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
