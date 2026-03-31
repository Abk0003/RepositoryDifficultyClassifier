# Repository Issue Difficulty Classifier

=======
A Flask web application that scrapes open GitHub issues from any public repository and automatically classifies each one as **Easy**, **Medium**, or **Hard** ,using a heuristic algorithm.

<img width="1920" height="1200" alt="Screenshot (30)" src="https://github.com/user-attachments/assets/d252ff44-3ce8-485f-9279-70d57393c472" />
<img width="1920" height="1200" alt="Screenshot (31)" src="https://github.com/user-attachments/assets/a1783414-d4b3-48d4-937f-88de1527efb9" />
<img width="1920" height="1200" alt="Screenshot (32)" src="https://github.com/user-attachments/assets/c58c8da2-adc0-40fd-baa1-0a75b5a06530" />

---

## What it does

1. Takes a GitHub repository URL as input (e.g. `https://github.com/scrapy/scrapy`).
2. Scrapes all open issues via the GitHub REST API.
3. Runs each issue through a scoring algorithm that reads the title, body, labels, and comment count.
4. Classifies each issue as **Easy**, **Medium**, or **Hard** and stores it in a local SQLite database.
5. Serves a web UI where you can filter issues by difficulty, search by keyword, and filter by date range and show  pie chart distribution.
6. Re-submitting a repo you've already scraped loads instantly from the database.

---

## Project structure

```
RepositoryIssueDifficultyClassifier/                      
├── webapp/
|    └── scrapper.py
|    └── classifier.py
|    └── app.py
|    └── templates/
|       └── index.html
|    └── static/
|        └── script.css
|        └── script.js
|    └── issues.db
├── requirements.txt
└── README.md
```

---

## Setup

### 1. Clone the repository

```bash
git clone https://github.com/ABK0003/RepositoryIssueDifficultyClassifier
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

The app calls the GitHub REST API to fetch issues using tokens .  A token is a credential that validates your authenticity to GitHub. Without a token, GitHub limits you to **60 requests per hour** which with 100 issues per API call translate to 6000 issues. With a token, the limit rises to **5000 requests per hour** that means 500000 issue repo can also be scraped increasing our website functionality.

Generate one at `https://github.com/settings/tokens`. Only the `public_repo` read scope is needed.

**Windows PowerShell (current session only):**
```powershell
$env:GITHUB_TOKEN = "enter token"
```

**Windows PowerShell (permanent — survives terminal restarts):**
```powershell
[System.Environment]::SetEnvironmentVariable("GITHUB_TOKEN", "enter token", "User")
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
2. Click **Fetch Issues** — the app fetches all open issues, classifies each one, and stores them
3. Browse the results table, which shows title, difficulty badge, label, comment count, and a direct link to the issue on GitHub
4. Use the filters at the top to narrow results:
   - **Difficulty** — show only Easy, Medium, or Hard issues
   - **Search** — full-text search across issue titles and bodies
   - **Date range** — filter by last updated date
5. Submitting a repo URL that has already been scraped skips the API entirely and loads from the local database immediately

---

## API endpoints

The Flask server uses four REST endpoints consumed by the frontend.

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/scrape` | Scrape and classify all open issues for a given repo URL |
| `GET` | `/api/issues` | Fetch stored issues with optional query filters |
| `GET` | `/api/stat` | Get the Easy / Medium / Hard count breakdown |
| `GET` | `/api/repos` | List all repos that have been scraped and stored |

### `/api/scrape` request body

```json
{ "url": "https://github.com/scrapy/scrapy" }
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
Each issue is scored by `classifier.py` using a **heuristic**. The score is a weighted sum of five parameters including length of body, engagement, title_hardness etc.

### Why not use an ML model?

With no labelled training data, a supervised ML model is not trainable. A heuristic uses patterns like keyword usage, body length etc is more explainable and easily implementable.

### The five parameters

#### Parameter 1 — GitHub labels (highest weight)

Developers label issues after reading the full codebase context. Their judgment is more reliable than any algorithm. If an issue has an explicit difficulty label, the score is overridden entirely:

```python
HARD_LABELS = {
    "hard", "complex", "expert", "difficulty: hard", "high complexity",
    "needs expertise", "senior", "advanced", "critical", "security",
    "performance", "breaking change"
}

EASY_LABELS = {
    "good first issue", "beginner", "easy", "difficulty: easy",
    "help wanted", "starter", "low hanging fruit", 
}

MED_LABELS = {
    "difficulty: medium", "intermediate", "medium", "moderate",
    "some experience", "needs context", "contributor friendly",
    "help needed", "second issue", "needs testing"
}
```

hard label → score is forced to `4.0` .
easy label → score is forced to `0.0` .
medium label → score is forced to `1.0`.

#### Signal 2 — Title keyword matches (high weight)

The issue title is a short summary.  This parameter uses **match count**, a title with one hard keyword scores `4.0` whether the title is 3 words or 15 words. Each title label has very high priority because these words are carefully chosen and supposed represent the entire issue.  

```
title_score = (4.0 × hard matches) − (2.0 × easy matches) + (1.0 × medium matches)
```

Hard keywords include: `segfault`, `memory leak`, `race condition`, `deadlock`, `cryptography`, `vulnerability`, `distributed`, `concurrency`, `kernel`, `compiler` and others.

Easy keywords include: `typo`, `documentation`, `readme`, `comment`, `spelling`, `formatting`, `cleanup`, `trivial`, `beginner`, `simple` and others.

#### Signal 3 — Body keyword density (medium weight)

The issue body is larger than the title — it contains buffer words, auto-generated logs, and code snippets. Keyword count is misleading here because a 1000-word body naturally contains more matches than a 50-word body even for the same issue.

The fix is to normalise by word count:

```
hard_den = (hard matches in body / total body words) × 100
body_score = (2.0 × body_hard_density) − (1.0 × body_easy_density) + (0.5 × body_med_density)
```

The body body is weighted at half the title density to reflect its lower reliability.

#### Signal 4 — Comment count (low weight)

Issues that generate significant discussion tend to have large discussions associated with them.

Comment count is log-scaled to capture diminishing returns — going from 0 to 5 comments is much more meaningful than going from 50 to 55. Normalised against a ceiling of 20:

```
engagement = (log(comment_count + 1) / log(20))
```

0 comments contributes `0.0` and 20 comments comments contributes exactly `1.0`. 

#### Signal 5 — Body length (lowest weight)

Longer issue descriptions suggest the reporter needed more context to explain the problem, which correlates with complexity. A one-line issue body is simpler than a detailed 1500-character bug report.

```
length_signal = 0.5 × (log(body_length + 1) / log(2000))
```

The `log(2000)` denominator normalises against a 2000-character limit using the same `log(max + 1)` technique as used in comment count.

### Final score combination

```
score = (2.0 × title_score) + (1.0 × body_score) + engagement + length_signal
```

### Hard floor

If two or more distinct hard keywords appear anywhere in the issue (title + body combined), the score is floored at `0.6` regardless of easy keyword count:

```python
MEDIUM_FLOOR = 0.6 

if total_hard_matches >= 2:
    score = max(score, MEDIUM_FLOOR)
```
Even if a task contains 10 eay keywords it cant be classified as easy if it has two hard key words associated with it so that is why this edge case is introduced

The floor is `0.6` rather than exactly `0.5` to avoid floating point edge cases — a computed value of `0.4999...` would slip under the `< 0.5` Easy threshold without this buffer.

### Classification thresholds

| Score | Classification | What it means |
|-------|---------------|---------------|
| < 0.5 | Easy | Easy keywords dominate, short body, low discussion  |
| 0.5 – 3.0 | Medium | Mixed signals, some technical content  |
| ≥ 3.0 | Hard | Hard keywords present, detailed body, active discussion  |

---

## Database Structure

Issues are stored in `issues.db`, a SQLite file created automatically when the app starts. No database setup is required.

```sql
CREATE TABLE issues (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    repo          TEXT,           -- e.g. "scrapy/scrapy"
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
---

## Requirements

```
flask
flask-cors
requests
pandas
numpy
```

Install with:

```bash
pip install -r requirements.txt
```

---

## Known limitations

- The time required for scraping is large for larger repositories. For example a numpy repo with 2100 issues took 75 s for scraping the first time which is very large infact it triggered the client to shut down request. To counter that right now, I have introduced a abortion timer which manually sets the time limit to 120 sec. This is a major issue as for any seemless user experience we need a time of response of 10 sec maximum.
- Classification is keyword-based so domain-specific repos may have terminology not covered by the keyword lists although the lists in `classifier.py` can be extended for specific domains.
-Labels need to have actual words that are present in github. To make it actually effective we need to added huge amounts of labels and keywords in our list which will have to beiteratively checked agaisnt each word. This makes the process very slow as mentioned in the first point.
- Re-scraping a repo that already exists in the database is skipped entirely to avoid redundant API calls. However to initiate rescraping again you would have to manually delete the repo from database from backend. 
- The scoring algorithm is heuristic so weights attached to each parameters are based on my understanding of teh issue that may very well be wrong in some edge cases. An issue titled *"fix segfault in beginner tutorial"* will score Medium due to the hard floor, which may or may not reflect the actual difficulty.
