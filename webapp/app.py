from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
import sqlite3
import pandas as pd
import os
print("importing scraper...")
from scraper import scrapeIssues
print("importing classifier...")
from classifier import classify
print("both imported successfully")


app = Flask(__name__,
    template_folder=os.path.join(os.path.dirname(__file__), "templates"),
    static_folder=os.path.join(os.path.dirname(__file__), "static")
)
CORS(app)

@app.route("/")
def home():
    return render_template("index.html")

def getdb():
    conn = sqlite3.connect("issues.db")
    conn.row_factory = sqlite3.Row
    return conn

def createdb():
    conn = getdb()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS issues (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            repo          TEXT,
            issue_no      INTEGER,
            labels        TEXT,
            title         TEXT,
            body          TEXT,
            comment_count INTEGER DEFAULT 0,
            last_updated  TEXT,
            difficulty    TEXT,
            url           TEXT
        )
    """)
    conn.commit()
    conn.close()

createdb()

@app.route("/api/scrape", methods=["POST"])
def scrape():
    data = request.get_json()
    url  = data.get("url", "").strip()

    if not url:
        return jsonify({"error": "No URL provided"}), 400

    parts = url.rstrip("/").split("/")
    repo  = f"{parts[-2]}/{parts[-1]}"

    conn   = getdb()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM issues WHERE repo = ?", (repo,))
    count  = cursor.fetchone()[0]
    conn.close()

    if count > 0:
        return jsonify({"message": f"Loaded {count} existing issues", "repo": repo})

    try:
        issues = scrapeIssues(url)
        print(f"SCRAPED: {len(issues)} issues")
        if not issues:
            return jsonify({"error": "No issues found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500

    conn   = getdb()
    cursor = conn.cursor()
    done   = 0

    try:
        for row in issues:
            cursor.execute(
                "SELECT id FROM issues WHERE repo = ? AND issue_no = ?",
                (repo, int(row["number"]))
            )
            if cursor.fetchone():
                continue
            difficulty = classify(row["title"], row["body"], row["comment_count"],row["labels"])
            cursor.execute("""
                INSERT INTO issues (repo, issue_no, title, body, labels, comment_count, last_updated, difficulty, url)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                repo,
                int(row["number"]),
                row["title"],
                row["body"],
                row["labels"],
                int(row["comment_count"]),
                row["last_updated"],
                difficulty,
                row["url"],
            ))
            done += 1
        conn.commit()
    except Exception as e:
        conn.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()

    return jsonify({"message": f"Added {done} issues", "repo": repo})

@app.route("/api/issues", methods=["GET"])
def issues():
    conn   = getdb()
    cursor = conn.cursor()

    dif    = request.args.get("difficulty")
    s      = request.args.get("search")
    r      = request.args.get("repo")
    date_f = request.args.get("date_from")
    date_t = request.args.get("date_to")

    cond = []
    par  = []

    if dif:
        cond.append("difficulty = ?")
        par.append(dif)
    if date_f:
        cond.append("last_updated >= ?")
        par.append(date_f)
    if date_t:
        cond.append("last_updated <= ?")
        par.append(date_t)
    if s:
        cond.append("(title LIKE ? OR body LIKE ?)")
        par.extend([f"%{s}%", f"%{s}%"])
    if r:
        cond.append("repo = ?")
        par.append(r)

    query = "SELECT * FROM issues"
    if cond:
        query += " WHERE " + " AND ".join(cond)
    query += " ORDER BY last_updated DESC"

    cursor.execute(query, par)
    rows = cursor.fetchall()
    conn.close()
    return jsonify([dict(i) for i in rows])

@app.route("/api/stat", methods=["GET"])
def stat():
    conn   = getdb()
    cursor = conn.cursor()

    r     = request.args.get("repo")
    query = "SELECT difficulty, COUNT(*) as count FROM issues"
    par   = []

    if r:
        query += " WHERE repo = ?"
        par.append(r)

    query += " GROUP BY difficulty"
    cursor.execute(query, par)
    rows = cursor.fetchall()
    conn.close()

    result = {"Easy": 0, "Medium": 0, "Hard": 0}
    for row in rows:
        result[row["difficulty"]] = row["count"]

    return jsonify(result)

@app.route("/api/repos", methods=["GET"])
def repos():
    conn   = getdb()
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT repo FROM issues")
    rows = cursor.fetchall()
    conn.close()
    return jsonify([row["repo"] for row in rows])

if __name__ == "__main__":
    app.run(debug=True)