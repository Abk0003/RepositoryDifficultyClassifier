import re
import math

HARD_LABELS = [
    "hard", "complex", "expert", "difficulty: hard",
    "high complexity", "needs expertise", "senior", "advanced",
    "critical", "security", "performance", "breaking change",
    "needs investigation", "deep dive", "research needed",
    "infrastructure", "scalability", "requires design"
]
EASY_LABELS = [
    "good first issue", "beginner", "easy", "difficulty: easy",
    "help wanted", "starter", "low hanging fruit", "first-timers-only",
    "trivial", "minor", "quick fix", "hacktoberfest", "up for grabs",
    "small", "beginner friendly", "easy fix", "newbie", "introductory",
    "documentation", "typo", "good-first-pr", "entry level"
]
MED_LABELS = [
    "difficulty: medium", "intermediate", "medium",
    "moderate", "some experience", "needs context",
    "contributor friendly", "help needed", "second issue",
    "needs testing", "needs review", "improvement",
    "enhancement", "refactor", "optimization"
]

SOL_PHRASES = ["we should", "fix would be", "proposed", "solution", "workaround", "suggest"]
TRACE_WORDS = ["traceback", "error:", "exception:", "panic:", "at ", r"file \""]
EXTS = [".py", ".js", ".ts", ".tsx", ".jsx", ".go", ".rs", ".c", ".cpp", ".h",
        ".java", ".rb", ".yml", ".yaml", ".json", ".toml", ".md", ".css", ".html"]

def match_label(labels, label_list):
    lset = []
    for l in labels.split(","):
        if l.strip() is not None:
            lset.append(l.strip().lower())
    for l in lset:
        if l in label_list:
            return True
    return False

def count_files(body):
    found = []
    for word in body.split():
        word = word.strip(r"(),;:\[]{}|`")
        if "/" not in word:
            continue
        letters = word.split("/")
        if len(letters) < 2:
            continue
        last = letters[-1]
        dot = last.rfind(".")
        if dot == -1:
            continue
        ext = last[dot:].lower()
        if ext in EXTS and word not in found:
            found.append(word)

    return len(found)

def countblocks(body):
    count = 0
    flag = False
    for line in body.split("\n"):
        if line.strip().startswith("```"):
            if flag:
                count += 1
            flag = not flag
    return count

def counttraces(body):
    count = 0
    for line in body.lower().split("\n"):
        for word in TRACE_WORDS:
            if word in line:
                count += 1
                break
    return count

def countrefs(body):
    found = []
    count = 0
    for word in body.split():
        if word.startswith("#"):
            num = word[1:].strip(r".,;:)]}\"'")
            if num.isdigit() and 1 <= len(num) <= 6 and num not in found:
                found.append(num)
    return len(found)

def has_sol(body):
    low = body.lower()
    for phrase in SOL_PHRASES:
        if phrase in low:
            return True
    return False

def computeScore(title,body,cc):
    if body is None:
         b = ""
    else:
        b = body
    files = count_files(b)
    blocks = countblocks(b)
    traces = counttraces(b)
    refs = countrefs(b)
    sol = has_sol(b)
    lenb = len(b)

    s = min(files/4,1.0)*3.0
    c = min(traces/5,1.0)*2.0
    d = min(blocks/3,1.0)*1.5
    con = min(refs / 3, 1.0) * 1.5
    dis = min(math.log1p(cc) / math.log1p(15), 1.0) * 2.0
    bulk = min(lenb/ 2000, 1.0) * 1.0
    cla = -1.5 if (sol and files <= 1 and traces == 0) else 0

    tech = s + c + d + con
    nont = dis + bulk + cla

    if tech < 1.5:
        nontechnical = min(nont, 1.5)

    return tech + nont

def classify(title,body,comment_count,labels):
    if match_label(labels, HARD_LABELS): return "Hard"
    if match_label(labels, EASY_LABELS): return "Easy"
    if match_label(labels, MED_LABELS):  return "Medium"

    s = computeScore(title, body, comment_count)

    if s < 2.0:  return "Easy"
    if s < 3.0:  return "Medium"
    return "Hard"