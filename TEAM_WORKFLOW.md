# Team Workflow

This repository uses a lightweight GitHub Flow process so multiple teammates can work safely in the same codebase.

## 1. Branching Strategy

- `main` is the stable branch.
- All work happens in short-lived branches created from `main`.
- Recommended branch names:
  - `feature/<issue-number>-<short-description>`
  - `fix/<issue-number>-<short-description>`
  - `docs/<short-description>`
  - `chore/<short-description>`

Examples:

- `feature/12-delay-analysis`
- `fix/18-null-delivery-time`
- `docs/update-readme`

Rules:

- Do not commit directly to `main`.
- Keep each branch focused on one task.
- Delete the branch after the pull request is merged.

## 2. GitHub Issues

Every task should start as a GitHub issue.

Each issue should include:

- A clear title.
- A short description of the problem or feature.
- Acceptance criteria.
- Labels such as `feature`, `bug`, `docs`, or `priority-high`.
- One assignee responsible for the work.

Recommended issue format:

- What needs to change.
- Why it matters.
- What the finished result should look like.
- Any datasets, files, or UI screens affected.

## 3. Pull Request Workflow

Use a pull request for every branch before merging to `main`.

PR checklist:

- Link the related issue.
- Explain what changed.
- Mention how you tested it.
- Ask at least one teammate for review.
- Resolve feedback before merging.

PR rules:

- Include `Closes #<issue-number>` in the PR description.
- Merge only after approval.
- Prefer squash merge if the team wants a cleaner history.

## 4. Commit Message Convention

Use conventional commits so the history is easy to read.

Format:

`type: short description`

Common types:

- `feat` for a new feature.
- `fix` for a bug fix.
- `docs` for documentation updates.
- `refactor` for code cleanup without behavior changes.
- `test` for test additions or updates.
- `chore` for maintenance work.

Examples:

- `feat: add SLA risk chart`
- `fix: correct late delivery calculation`
- `docs: add workflow guide`
- `refactor: simplify delay summary logic`

## 5. Team Operating Rules

- Open an issue before starting work.
- Push early so teammates can see progress.
- Review before merge.
- Keep commits small and descriptive.
- Update the issue and PR when requirements change.

## 6. Suggested Sprint Flow

1. Create an issue.
2. Create a branch from `main`.
3. Make focused commits.
4. Push the branch to GitHub.
5. Open a pull request.
6. Review the PR with at least one teammate.
7. Merge after approval.
8. Delete the branch.
