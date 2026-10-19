# Contributing to Radicle

Thanks for wanting to help! 🌱 Radicle is a community project. Bug reports, docs, translations, design and code all count, and first-time contributors are very welcome.

<p align="center"><img src="docs/images/contributing-flow.svg" alt="How a change gets in" width="900"></p>

## Contents

- [Ways to help](#ways-to-help)
- [Ground rules for pull requests](#ground-rules-for-pull-requests)
- [Branch names](#branch-names)
- [Commit messages](#commit-messages)
- [Step by step](#step-by-step)
- [Set up your environment](#set-up-your-environment)
- [Code rules](#code-rules)
- [Tests](#tests)
- [Reviews and merging](#reviews-and-merging)
- [Reporting bugs and security issues](#reporting-bugs-and-security-issues)
- [License of your contributions](#license-of-your-contributions)

## Ways to help

- **Report a bug**: open an issue with the steps to reproduce it, what you expected and what happened. Add screenshots if you can.
- **Propose a feature**: open an issue first and describe the problem it solves. We agree on the idea before anyone writes code, so nobody's work gets thrown away.
- **Pick an issue**: look for the `good first issue` and `help wanted` labels, or the [known issues in the README](README.md#%EF%B8%8F-roadmap-and-known-issues). Comment on the issue so others know you are on it.
- **Improve the docs or translations**: the UI is in English and Spanish (`frontend/src/i18n/locales/`), and both READMEs welcome fixes.

## Ground rules for pull requests

Small and focused PRs get reviewed fast and break less. Every PR must:

| Rule | Why |
| --- | --- |
| **Do one thing.** A feature, a fix or a refactor, never a mix. | It can be reviewed, reverted and understood on its own. |
| **Change fewer than 500 lines** (added + removed). | A reviewer can read it carefully in one sitting. |
| **Touch fewer than 100 files.** | Same reason, and it keeps conflicts small. |
| **Include tests** for what it adds or fixes. | It proves the change works and keeps it working. |
| **Pass CI**: lint, types, unit, integration and E2E tests. | `main` is always releasable. |

Generated and vendored files do not count toward the limits: `pnpm-lock.yaml`, `uv.lock`, `frontend/openapi.json`, `frontend/src/services/api/schema.d.ts`, `frontend/tsconfig.tsbuildinfo` and images in `docs/images/`. A CI check (`PR size`) measures every PR.

**Bigger work?** Split it into a chain of PRs, each one useful and green on its own. For example: first the migration and the service with tests, then the API, then the UI. If something cannot be split, explain why in the PR and a maintainer can make an exception.

## Branch names

Name branches `type/short-description`, in lowercase with dashes:

| Type | Use it for | Example |
| --- | --- | --- |
| `feat/` | Something new: a feature, an endpoint, a screen, an MCP tool. | `feat/changing-x-y`, `feat/csv-import` |
| `minor/` | Small changes and tweaks: copy, styles, small UX touches, dependency bumps. | `minor/board-card-spacing` |
| `fix/` | A bug fix. | `fix/burndown-backdated-sprint` |
| `refactor/` | Reordering or cleaning code **without** changing behavior. | `refactor/split-ticket-service` |
| `docs/` | Documentation only. | `docs/sso-okta-guide` |

The `PR size` check also validates the branch name.

## Commit messages

Use [Conventional Commits](https://www.conventionalcommits.org/), in English:

```text
feat(inbox): let admins reopen discarded items
fix(reports): start the burndown on the real sprint start
refactor(tickets): move field validation to its own module
docs(readme): add an Okta example to the SSO guide
chore(deps): bump recharts to 3.10.2
```

| Branch type | Commit type |
| --- | --- |
| `feat/` | `feat:` |
| `minor/` | `chore:` (or `style:` for pure formatting) |
| `fix/` | `fix:` |
| `refactor/` | `refactor:` |
| `docs/` | `docs:` |

Tests can go in the same commit or in a `test:` commit in the same PR. PRs are squash-merged, so the **PR title** becomes the final commit message: write it as a Conventional Commit too.

## Step by step

1. **Fork** the repository and clone your fork.
2. **Create a branch** from an up-to-date `main`:
   ```bash
   git switch main && git pull upstream main
   git switch -c fix/burndown-backdated-sprint
   ```
3. **Make the change** with its tests. Run the checks locally (see [Tests](#tests)).
4. **Push** and open a **pull request** against `main`. Fill in the template: what changes, why, how you tested it and screenshots for UI changes. Link the issue (`Closes #123`).
5. **Keep it green.** If CI fails, push fixes to the same branch.
6. **Address the review**, then a maintainer squash-merges it. 🎉

Draft PRs are welcome when you want early feedback.

## Set up your environment

| Part | Needs |
| --- | --- |
| Backend | Python 3.12, [uv](https://docs.astral.sh/uv/), Docker (tests use real PostgreSQL) |
| Frontend | Node 22, pnpm 9 |

```bash
cp .env.example .env
echo "RADICLE_SECRET_KEY=$(openssl rand -hex 32)" >> .env
cp .env backend/.env

# Database and migrations
docker compose up -d db
cd backend && uv sync && uv run alembic upgrade head

# Backend at http://localhost:8000
uv run uvicorn radicle.main:app --reload

# Frontend at http://localhost:5173 (proxies the API to :8000)
cd ../frontend && pnpm install && pnpm dev
```

Want data to play with? `cd backend && uv run python ../scripts/seed.py --tickets 400 --project PA` creates a realistic project. Sign in as `fernando@example.com` / `radicle-demo`.

## Code rules

The design documents in [`docs/`](docs/) (in Spanish) explain the decisions behind Radicle. The rules that matter most day to day:

**Everywhere**

- Code, API, database names, comments and commit messages are in **English**.
- If a change goes against an existing decision, propose it in an issue first. Big decisions get an ADR in [`docs/decisions/`](docs/decisions/).
- Update `CHANGELOG.md` (under *Unreleased*) and the README when users will notice the change.

**Backend** (`backend/`)

- Business logic lives in `radicle/services/`. Routers (`radicle/api/`) and MCP tools (`radicle/mcp/`) only validate input and call services.
- Errors are raised as `ProblemError` (`radicle/core/errors.py`) with a message that tells the user what to do. They are returned as RFC 9457 problem details.
- Every schema change is an Alembic migration with both `upgrade` and `downgrade`.
- Permissions always go through `radicle/core/permissions.py`. Restricted tickets must never leak: if you add a `GET` route or an MCP tool, add it to `tests/integration/test_restricted.py`.
- `mypy --strict` passes on `services/` and `query/`. Format with `ruff format`.

**Frontend** (`frontend/`)

- Styles use styled-components with the tokens in `src/styles/theme.ts`. No Tailwind and no loose colors.
- One folder per component: `index.tsx` without styles, `style.ts` (`import * as S from './style'`) and its tests.
- Files stay under 500 lines (ESLint `max-lines`). If one grows, split it into `components/` inside its folder.
- All visible text goes through i18n, in both `src/i18n/locales/en.json` and `es.json`.

## Tests

Each PR brings tests for what it changes:

- **Every endpoint**: a happy case, an error case and a permissions case.
- **Bugs**: a test that fails without the fix.
- **UI**: Vitest tests for components with logic. User journeys that cross screens go in Playwright (`frontend/e2e/`).
- Coverage stays at **85% or more** in `services/` and `query/`, and **70% or more** overall.

Run what CI runs:

```bash
cd backend && uv run ruff check . && uv run ruff format --check . && uv run mypy radicle && uv run pytest --cov
cd frontend && pnpm check && pnpm build
scripts/smoke.sh
```

Backend tests start PostgreSQL in Docker with testcontainers. Tests marked `slow` (SSO with Keycloak, performance) can be skipped locally with `-m "not slow"`. CI runs them all.

## Reviews and merging

- A maintainer reviews within a few days. A friendly ping on the PR after a week is fine.
- Reviews are about the code, never the person. Ask questions, explain the why, and suggest instead of demanding.
- At least one approval and green CI are needed to merge. PRs are squash-merged into `main`.

## Reporting bugs and security issues

- **Bugs**: open an issue with steps, expected and actual behavior, your Radicle version and logs if you have them.
- **Security issues**: do **not** open a public issue. Use GitHub's **private vulnerability reporting** (Security tab → *Report a vulnerability*). We will answer as soon as we can and credit you in the fix.

## License of your contributions

Radicle is licensed under the [GNU AGPL v3.0](LICENSE). By opening a pull request, you agree that your contribution is licensed under the same terms, and you confirm that you have the right to submit it.

Thank you for helping Radicle grow! 🌿
