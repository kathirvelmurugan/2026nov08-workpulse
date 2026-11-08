# WorkPulse SDLC — User Guide

## Table of Contents
1. [Quick Start](#quick-start)
2. [Projects & Work Items](#projects--work-items)
3. [SDLC Lifecycles](#sdlc-lifecycles)
4. [AI Pipeline](#ai-pipeline)
5. [Research & Exploration](#research--exploration)
6. [Bug Triage](#bug-triage)
7. [Testing & QA](#testing--qa)
8. [Technical Debt](#technical-debt)
9. [Sprints & Milestones](#sprints--milestones)
10. [Definition of Done](#definition-of-done)
11. [Incident Response](#incident-response)
12. [Admin Settings](#admin-settings)
13. [Retrospectives & Learning](#retrospectives--learning)

---

## Quick Start

### Start the system
```bash
# Terminal 1: Backend
cd server && python server.py
# → http://localhost:8080

# Terminal 2: Frontend
cd frontend && npm run dev
# → http://localhost:5173
```

### Create your first work item
1. Open http://localhost:5173
2. Click "+ New Work Item"
3. Select project, type (feature/bug/research/maintenance), add title + description
4. Click "Create & Start Pipeline"
5. The 7-phase AI pipeline auto-executes

---

## Projects & Work Items

### Project types
| Type | Use case |
|---|---|
| **internal** | Your own products (WorkPulse, factory tools) |
| **client** | Client-delivered projects (CRM for Acme Corp) |

### Work item types
| Type | Pipeline | Example |
|---|---|---|
| **feature** | Full 7-phase | "Build customer dashboard" |
| **bug** | Reproduce → Fix → Test → QA (4-phase) | "Login broken on Safari" |
| **research** | Research → ADR output | "Evaluate GraphQL vs REST" |
| **maintenance** | Fix → Test (2-phase) | "Update npm dependencies" |

### Creating a work item via API
```bash
curl -X POST http://localhost:8080/api/tasks \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Build login system",
    "task_type": "feature",
    "expected_output": "Email+password auth with JWT tokens",
    "project_id": "your-project-id",
    "priority_order": 1
  }'
```

---

## SDLC Lifecycles

### Configurable per project

Each project can have a custom lifecycle. Default is the full 7-phase pipeline:

```
architect → reviewer → backend → frontend → database → tests → qa
```

### Customizing via settings
```bash
curl -X POST http://localhost:8080/api/settings \
  -H "Content-Type: application/json" \
  -d '{
    "key": "lifecycle_project_crm",
    "value": "architect,reviewer,backend,frontend,qa"
  }'
```

### Available lifecycles
| Name | Phases | Use for |
|---|---|---|
| **full** | architect, reviewer, backend, frontend, database, tests, qa | New features |
| **quick** | architect, backend, frontend, qa | Simple features |
| **bugfix** | reproduce, architect, fix, test, qa | Bug fixes |
| **research** | research, adr_output | Research spikes |
| **migration** | audit, plan, migrate, test, qa | Refactoring |

---

## AI Pipeline

### How it works
1. **Architect** — Writes SPEC.md defining API contract, DB schema, file assignments, acceptance criteria
2. **Reviewer** — Critiques SPEC.md, writes REVIEW.md with APPROVED or REVISION_NEEDED
3. **Backend** — Builds API routes, middleware, auth logic
4. **Frontend** — Builds components, pages, connects to API
5. **Database** — Creates models, migrations, seed data
6. **Tests** — Writes integration + unit tests per acceptance criteria
7. **QA** — Reviews all code against SPEC.md. Reports PASS or FAIL with violations

### Running a pipeline phase manually
```bash
curl -X POST http://localhost:8080/api/pipeline/run/TASK_ID/architect
```

### Pipeline execution rules
- Each phase commits to git before the next phase starts
- Failed phases auto-retry (max 3 attempts)
- After 3 failures, task is "parked" for human review
- QA failures generate repair tasks automatically

---

## Research & Exploration

### When to use research work items
- Evaluating new technology ("React vs Vue for project X")
- Architecture decisions ("Monolith vs microservices")
- Feasibility studies ("Can we migrate from MySQL to PostgreSQL?")
- Tool evaluation ("Which state management library?")

### Research output format (ADR)
Every research task must produce an Architecture Decision Record:

```markdown
# ADR: [Title]

## Status
Proposed | Accepted | Deprecated | Superseded

## Context
What is the issue? Why do we need this decision?

## Decision
What did we decide? What approach?

## Consequences
What becomes easier? What becomes harder?

## Alternatives Considered
Option A, Option B — with pros/cons

## Recommendation
Clear recommendation with reasoning
```

### Running a research task
```bash
curl -X POST http://localhost:8080/api/tasks \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Research: GraphQL vs REST for new API",
    "task_type": "research",
    "expected_output": "ADR format: context, decision, consequences, alternatives, recommendation"
  }'
```

---

## Bug Triage

### Bug workflow
```
Bug Reported → Reproduce → Root Cause → Fix → Regression Test → QA → Merge
```

### Severity classification
| Severity | Criteria | Example |
|---|---|---|
| **critical** | Data loss, security breach, all users blocked | "Login endpoint exposes passwords" |
| **high** | Major feature broken, no workaround | "Payment processing fails" |
| **medium** | Feature broken, workaround exists | "Export PDF fails, CSV works" |
| **low** | Cosmetic, minor | "Button misaligned on mobile" |

### Bug reproduction verification (NEW)
Before fixing, the system verifies the bug exists:
1. Creates isolated environment from the reported commit
2. Runs the reproduction steps
3. Confirms failure before dispatching fix agent
4. After fix, runs regression test to confirm fix + no new breaks

### Creating a bug work item
```bash
curl -X POST http://localhost:8080/api/tasks \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Login fails on Safari 18.x",
    "task_type": "bug",
    "priority_order": 1,
    "expected_output": "Fix CORS error, verify on Safari 18.x, add regression test"
  }'
```

---

## Testing & QA

### Three layers of testing

| Layer | Who | What |
|---|---|---|
| **Unit tests** | Tests agent (Phase 6) | Individual functions, components |
| **Integration tests** | Tests agent (Phase 6) | API endpoints, DB queries |
| **Acceptance tests** | QA agent (Phase 7) | SPEC.md criteria verification |

### Exploratory testing (NEW)
QA agent now includes edge case generation:
- Boundary testing (empty strings, max values, null)
- Error path testing (invalid inputs, timeouts)
- Security checks (XSS, SQL injection patterns, exposed secrets)
- AGENTS.md rule compliance (password toggles, form validation, a11y)

### QA pass conditions
All of these must pass:
1. API matches SPEC.md contract exactly
2. Database schema matches SPEC.md
3. Frontend connects to all API endpoints
4. Tests cover every acceptance criterion
5. No critical or high-severity security findings
6. AGENTS.md rules followed (UI patterns, a11y, no console.log)
7. No exploratory edge case failures

### QA report format
```
PASS: All 23 acceptance criteria verified
FAIL: 3 violations found
  - [MEDIUM] api/auth/login.js:45 — Missing rate limiting
  - [LOW] frontend/Login.jsx:12 — No show/hide password toggle
  - [LOW] tests/auth.test.js — Missing edge case: empty email
```

---

## Technical Debt

### Tracking markers
Agents can mark code with technical debt:

```javascript
// @tech-debt: Using in-memory storage. Should migrate to SQLite before production.
// @priority: medium
// @owner: backend
const tasks = new Map();
```

### Debt dashboard
All `@tech-debt` markers are tracked in the database:
```bash
curl http://localhost:8080/api/tech-debt
```

Returns:
```json
[
  {
    "file": "backend/storage.js",
    "line": 12,
    "message": "In-memory storage, migrate to SQLite",
    "priority": "medium",
    "owner": "backend",
    "created_by": "AI Factory",
    "status": "open"
  }
]
```

### Debt resolution
```bash
# Create a maintenance work item from debt
curl -X POST http://localhost:8080/api/tasks \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Fix technical debt: migrate storage to SQLite",
    "task_type": "maintenance",
    "expected_output": "Replace in-memory Map with SQLite database"
  }'
```

---

## Sprints & Milestones

### Creating a milestone
```bash
curl -X POST http://localhost:8080/api/milestones \
  -H "Content-Type: application/json" \
  -d '{
    "project_id": "proj-001",
    "title": "Sprint 1 — MVP",
    "goal": "Working authentication + basic CRUD",
    "start_date": "2026-11-10",
    "end_date": "2026-11-24"
  }'
```

### Adding tasks to a milestone
```bash
curl -X PATCH http://localhost:8080/api/tasks/TASK_ID \
  -H "Content-Type: application/json" \
  -d '{"milestone_id": "milestone-001"}'
```

### Milestone progress view
```
Sprint 1 — MVP (Nov 10-24)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[████████░░░░░░░░░░░░] 40% complete

✅ Build login system        (merged)
✅ Build registration        (merged)
⏳ Build dashboard           (in_progress)
⬜ Add payment integration   (queued)
⬜ Deploy to staging         (queued)
```

---

## Definition of Done

### A work item is "done" when ALL of these pass:

```
□ 1. SPEC.md written and approved by reviewer
□ 2. All implementation files committed
□ 3. Build passes (npm run build)
□ 4. All tests pass (npm test)
□ 5. Lint clean (npm run lint)
□ 6. QA agent reports PASS
□ 7. No critical or high-severity findings
□ 8. Technical debt documented (if any)
□ 9. Changes merged to integration branch
□ 10. Acceptance criteria from SPEC.md verified
□ 11. No AGENTS.md rule violations
□ 12. Exploratory edge cases handled
```

### Deployment readiness (additional)
```
□ 13. Staging environment tested
□ 14. Database migrations tested
□ 15. Rollback plan documented
□ 16. Monitoring/alerting configured
□ 17. Documentation updated
```

---

## Incident Response

### Automated rollback
If a merged change causes issues:
```bash
# Rollback last merge
curl -X POST http://localhost:8080/api/incidents/rollback/TASK_ID
```

This:
1. Identifies the merge commit
2. Creates a revert commit
3. Creates a bug work item for investigation
4. Notifies the team

### Incident lifecycle
```
Incident detected → Rollback (if critical) → Bug work item created → 
Root cause analysis → Fix → Regression test → QA → Re-deploy
```

### Manual rollback
```bash
cd your-project
git log --oneline -5  # find the merge commit
git revert -m 1 <merge-commit-hash>
git push
```

---

## Admin Settings

### Configuration endpoints
```bash
# View all settings
curl http://localhost:8080/api/settings

# Set a setting
curl -X POST http://localhost:8080/api/settings \
  -H "Content-Type: application/json" \
  -d '{"key": "default_model", "value": "qwen3.8-max", "label": "Default AI Model"}'

# Set lifecycle configuration
curl -X POST http://localhost:8080/api/settings \
  -H "Content-Type: application/json" \
  -d '{
    "key": "lifecycle_project_default",
    "value": "architect,reviewer,backend,frontend,database,tests,qa",
    "label": "Default Project Lifecycle"
  }'
```

### Available admin settings
| Key | Default | Description |
|---|---|---|
| `default_model` | qwen3.8-max | AI model for agents |
| `max_retries` | 3 | Max retry attempts per phase |
| `agent_timeout` | 3600 | Agent timeout in seconds |
| `lifecycle_project_default` | Full 7-phase | Default lifecycle for projects |
| `auto_advance` | true | Auto-advance pipeline phases |
| `require_reviewer` | true | Require reviewer approval |
| `geofence_radius_meters` | 500 | Location validation radius |
| `whatsapp_enabled` | false | Enable WhatsApp notifications |
| `daily_summary_time` | 08:00 | Time for daily summaries |
| `points_starting_balance` | 1000 | Starting points for new members |

---

## Retrospectives & Learning

### How the system learns

After every pipeline completion, the system records:
- What worked (phases that completed on first attempt)
- What failed (phases that needed retries)
- Common failure patterns (e.g., "architect forgot error states 3 times this week")
- Token usage by role (for cost optimization)

### Viewing retrospectives
```bash
curl http://localhost:8080/api/retrospectives?project_id=PROJ_ID
```

### Learning loop actions
When a pattern is detected:
1. AGENTS.md is auto-updated with the fix rule
2. Future agents see the updated rule
3. Success rate is tracked per rule

### Example: Learning from failures
```
Pattern detected: Architect forgets error states (3/5 projects)
Action: Added to AGENTS.md → "Always include error states in API contract"
Result: Error state compliance improved from 40% to 85%
```

### Resetting the factory
```bash
# Clean up all worktrees and temporary data
rm -rf worktrees/
rm -f factory.db

# Git cleanup
cd your-project
git worktree prune
```

---

## Appendix: API Reference

### Authentication
| Method | Endpoint | Description |
|---|---|---|
| POST | /api/auth/register | Register new user |
| POST | /api/auth/login | Login, get token |
| GET | /api/auth/me | Current user info |

### Tasks
| Method | Endpoint | Description |
|---|---|---|
| GET | /api/tasks | List tasks (filter by status, project, type) |
| POST | /api/tasks | Create task |
| GET | /api/tasks/:id | Get task detail (with messages, sessions) |
| PATCH | /api/tasks/:id | Update task status/fields |

### Pipeline
| Method | Endpoint | Description |
|---|---|---|
| POST | /api/pipeline/run/:task_id/:role | Execute pipeline phase |

### Projects
| Method | Endpoint | Description |
|---|---|---|
| GET | /api/projects | List projects |
| POST | /api/projects | Create project |

### Team
| Method | Endpoint | Description |
|---|---|---|
| GET | /api/team | List team members |
| POST | /api/team | Add team member |
| PATCH | /api/team/:id | Update member |

### Settings
| Method | Endpoint | Description |
|---|---|---|
| GET | /api/settings | List settings |
| POST | /api/settings | Set setting |

### Incidents
| Method | Endpoint | Description |
|---|---|---|
| POST | /api/incidents/rollback/:task_id | Rollback merge |

---

**Last updated:** November 9, 2026
**Version:** 1.0