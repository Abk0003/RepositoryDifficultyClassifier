# Repository Issue Difficulty Classifier

A Flask web application that scrapes open GitHub issues from any public repository and automatically classifies each one as **Easy**, **Medium**, or **Hard** — using a multi-signal heuristic scoring algorithm built entirely without a machine learning model.

The core idea: instead of manually triaging hundreds of GitHub issues to find beginner-friendly ones, this tool does it automatically by analysing the language used in issue titles, bodies, labels, and engagement metrics.

---

## What it does

1. Takes a GitHub repository URL as input (e.g. `https://github.com/numpy/numpy`)
2. Scrapes all open issues via the GitHub REST API — skipping pull requests
3. Runs each issue through a scoring algorithm that reads the title, body, labels, and comment count
4. Classifies each issue as **Easy**, **Medium**, or **Hard** and stores it in a local SQLite database
5. Serves a web UI where you can filter issues by difficulty, search by keyword, and filter by date range
6. Caches results — re-submitting a repo you've already scraped loads instantly from the database with no redundant API calls

---

## Project structure

```
RepositoryIssueDifficultyClassifier/
├── app.py           # Flask server — all API routes and SQLite database logic
├── scraper.py       # GitHub API client — paginates and fetches all open issues
├── classifier.py    # Scoring algorithm — the core logic that assigns Easy/Medium/Hard
├── issues.db        # SQLite database, auto-created on first run
├── templates/
│   └── index.html   # Frontend UI — search, filter, browse classified issues
├── requirements.txt
└── README.md
```

---

## Setup

### 1. Clone the repository

```bash
git clone https://github.com/YOUR_USERNAME/RepositoryIssueDifficultyClassifier
cd RepositoryIssueDifficultyClassifier
```

### 2. Create and activate a virtual environment

Using a virtual environment keeps dependencies isolated from your system Python installation.

```bash
python -m venv .venv

# Windows PowerShell
.venv\Scripts\Activate.ps1

# macOS / Linux
source .venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Set your GitHub token

The app calls the GitHub REST API to fetch issues. Without a token, GitHub limits you to **60 requests per hour** — not enough to scrape a large repo. With a token, the limit rises to **5000 requests per hour**.

A token is a scoped credential — it proves to GitHub that you are a real authenticated user without exposing your actual password. You can revoke it at any time without affecting your account.

Generate one at `https://github.com/settings/tokens`. Only the `public_repo` read scope is needed.

**Windows PowerShell (current session only):**
```powershell
$env:GITHUB_TOKEN = "your_token_here"
```

**Windows PowerShell (permanent — survives terminal restarts):**
```powershell
[System.Environment]::SetEnvironmentVariable("GITHUB_TOKEN", "your_token_here", "User")
```

**macOS / Linux:**
```bash
export GITHUB_TOKEN="your_token_here"
```

> **Important:** Never hardcode your token directly in source files and never commit it to git. Even in a private repo, tokens in source code are a security risk. The app reads it from the environment variable `GITHUB_TOKEN` automatically via `os.environ.get("GITHUB_TOKEN")`.

### 5. Run the app

```bash
python app.py
```

Open `http://localhost:5000` in your browser.

---

## Usage

1. Paste any public GitHub repository URL into the input field
2. Click **Scrape** — the app fetches all open issues, classifies each one, and stores them
3. Browse the results table, which shows title, difficulty badge, label, comment count, and a direct link to the issue on GitHub
4. Use the filters at the top to narrow results:
   - **Difficulty** — show only Easy, Medium, or Hard issues
   - **Search** — full-text search across issue titles and bodies
   - **Date range** — filter by last updated date
5. The stats bar at the top shows the Easy / Medium / Hard breakdown for the current view
6. Submitting a repo URL that has already been scraped skips the API entirely and loads from the local database immediately

---

## API endpoints

The Flask server exposes four REST endpoints consumed by the frontend.

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/scrape` | Scrape and classify all open issues for a given repo URL |
| `GET` | `/api/issues` | Fetch stored issues with optional query filters |
| `GET` | `/api/stat` | Get the Easy / Medium / Hard count breakdown |
| `GET` | `/api/repos` | List all repos that have been scraped and stored |

### `/api/scrape` request body

```json
{ "url": "https://github.com/numpy/numpy" }
```

Returns a message confirming how many issues were added, or a message saying the repo was loaded from cache.

### `/api/issues` query parameters

| Parameter | Type | Example | Description |
|-----------|------|---------|-------------|
| `difficulty` | string | `Easy` | Filter by difficulty label |
| `search` | string | `memory` | Search issue title and body text |
| `repo` | string | `numpy/numpy` | Filter to a specific repo |
| `date_from` | string | `2023-01-01` | Issues updated on or after this date |
| `date_to` | string | `2024-01-01` | Issues updated on or before this date |

---

## How the classifier works

This is the most important part of the project. Each issue is scored by `classifier.py` using a **multi-signal heuristic** — not a machine learning model. The score is a weighted sum of five independent signals, each justified by a real-world observation about how GitHub issues are written.

### Why not use an ML model?

With no labelled training data (no ground truth "this issue is Hard"), a supervised ML model is not trainable. A heuristic grounded in observable patterns — keyword usage, maintainer labels, discussion volume — is more transparent, explainable, and deployable with zero training data.

### The five signals

#### Signal 1 — GitHub labels (highest trust, acts as override)

Maintainers label issues after reading the full codebase context. Their judgment is more reliable than any algorithm. If an issue has an explicit difficulty label, the score is overridden entirely:

```python
HARD_LABELS = {
    "hard", "complex", "expert", "difficulty: hard", "high complexity",
    "needs expertise", "senior", "advanced", "critical", "security",
    "performance", "breaking change", "needs investigation", "deep dive",
    "research needed", "infrastructure", "scalability", "requires design"
}

EASY_LABELS = {
    "good first issue", "beginner", "easy", "difficulty: easy",
    "help wanted", "starter", "low hanging fruit", "first-timers-only",
    "trivial", "minor", "quick fix", "hacktoberfest", "up for grabs",
    "small", "beginner friendly", "easy fix", "newbie", "introductory",
    "documentation", "typo", "good-first-pr", "entry level"
}

MED_LABELS = {
    "difficulty: medium", "intermediate", "medium", "moderate",
    "some experience", "needs context", "contributor friendly",
    "help needed", "second issue", "needs testing", "needs review",
    "improvement", "enhancement", "refactor", "optimization"
}
```

If a hard label is detected → score is forced to `4.0` (Hard).
If an easy label is detected → score is forced to `0.0` (Easy).
If a medium label is detected → score is forced to `1.0` (Medium).

#### Signal 2 — Title keyword matches (high trust, raw count)

The issue title is a deliberate compressed summary. Every word is chosen intentionally. This signal uses **raw match count**, not density — a title with one hard keyword scores `4.0` whether the title is 3 words or 15 words. Density would incorrectly penalise longer titles.

```
title_score = (4.0 × hard matches) − (2.0 × easy matches) + (1.0 × medium matches)
```

Hard keywords include: `segfault`, `memory leak`, `race condition`, `deadlock`, `cryptography`, `vulnerability`, `distributed`, `concurrency`, `kernel`, `compiler` and others.

Easy keywords include: `typo`, `documentation`, `readme`, `comment`, `spelling`, `formatting`, `cleanup`, `trivial`, `beginner`, `simple` and others.

#### Signal 3 — Body keyword density (medium trust, normalised)

The issue body is noisier than the title — it contains boilerplate templates, pasted stack traces, auto-generated logs, and code snippets. Raw keyword count is misleading here because a 1000-word body naturally contains more matches than a 50-word body even for the same issue complexity.

The fix is to normalise by word count:

```
body_hard_density = (hard matches in body / total body words) × 100
body_score = (2.0 × body_hard_density) − (1.0 × body_easy_density) + (0.5 × body_med_density)
```

The body signal is weighted at half the title signal (`2.0` vs `4.0` per match) to reflect its lower reliability.

#### Signal 4 — Comment count (low trust, tiebreaker)

Issues that generate significant discussion tend to be harder — they require clarification, have competing approaches debated, or have failed fix attempts. A simple typo fix does not get fifteen replies.

Comment count is log-scaled to capture diminishing returns — going from 0 to 5 comments is much more meaningful than going from 50 to 55. Normalised against a ceiling of 20:

```
engagement = 1.0 × (log(comment_count + 1) / log(21))
```

At 0 comments → contributes `0.0`. At 20 comments → contributes exactly `1.0`. Beyond 20 → still grows but slowly. The `log(21)` denominator is `log(ceiling + 1)` which squishes the output to a `0 → 1` range at the ceiling value.

#### Signal 5 — Body length (lowest trust, tiebreaker)

Longer issue descriptions suggest the reporter needed more context to explain the problem, which loosely correlates with complexity. A one-line issue body is probably simpler than a detailed 1500-character bug report with reproduction steps.

```
length_signal = 0.5 × (log(body_length + 1) / log(2001))
```

Contributes a maximum of `0.5` — purely a tiebreaker, not a primary signal. The `log(2001)` denominator normalises against a 2000-character ceiling using the same `log(ceiling + 1)` technique.

### Final score combination

```
score = (2.0 × title_score) + (1.0 × body_score) + engagement + length_signal
```

Title is weighted `2×` body because it is a more reliable source of signal — compressed, deliberate, and noise-free.

### Hard floor

If two or more distinct hard keywords appear anywhere in the issue (title + body combined), the score is floored at `0.6` regardless of easy keyword count:

```python
MEDIUM_FLOOR = 0.6  # just above the 0.5 Easy/Medium boundary

if total_hard_matches >= 2:
    score = max(score, MEDIUM_FLOOR)
```

This prevents adversarial cases like *"fix this minor memory leak typo in the beginner-friendly readme"* from being classified as Easy. An issue that genuinely references two hard technical concepts cannot be a beginner task.

The floor is `0.6` rather than exactly `0.5` to avoid floating point edge cases — a computed value of `0.4999...` would slip under the `< 0.5` Easy threshold without this buffer.

### Classification thresholds

| Score | Classification | What it means |
|-------|---------------|---------------|
| < 0.5 | Easy | Easy keywords dominate, short body, low discussion — suitable for first-time contributors |
| 0.5 – 3.0 | Medium | Mixed signals, some technical content — requires familiarity with the codebase |
| ≥ 3.0 | Hard | Hard keywords present, detailed body, active discussion — requires deep domain expertise |

---

## Database schema

Issues are stored in `issues.db`, a SQLite file created automatically when the app starts. No database setup is required.

```sql
CREATE TABLE issues (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    repo          TEXT,           -- e.g. "numpy/numpy"
    issue_no      INTEGER,        -- GitHub issue number
    labels        TEXT,           -- comma-separated label names
    title         TEXT,           -- issue title
    body          TEXT,           -- issue body (markdown)
    comment_count INTEGER DEFAULT 0,
    last_updated  TEXT,           -- YYYY-MM-DD format
    difficulty    TEXT,           -- "Easy", "Medium", or "Hard"
    url           TEXT            -- direct link to the issue on GitHub
)
```

To wipe and re-classify a repo, delete its rows manually:

```sql
DELETE FROM issues WHERE repo = 'numpy/numpy';
```

Then re-submit the URL in the UI to trigger a fresh scrape and classification.

---

## Requirements

```
flask
flask-cors
requests
pandas
```

Install with:

```bash
pip install -r requirements.txt
```

---

## Known limitations

- Only scrapes **open** issues. Closed issues are not fetched or classified.
- Classification is keyword-based — domain-specific repos (compilers, game engines, embedded systems) may have terminology not covered by the keyword lists. The lists in `classifier.py` can be extended for specific domains.
- Re-scraping a repo that already exists in the database is skipped entirely to avoid redundant API calls. Delete the repo's rows from `issues.db` to force a fresh classification.
- GitHub API rate limit is 5000 requests/hour with a token. At 100 issues per request, a repo with 5000+ issues will require 50+ API calls and may approach the limit in a single session.
- The scoring algorithm is heuristic — it will misclassify edge cases. An issue titled *"fix segfault in beginner tutorial"* will score Medium due to the hard floor, which may or may not reflect the actual difficulty.
