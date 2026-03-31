import math

HARD = [
    "segfault", "memory leak", "race condition", "deadlock", "undefined behavior",
    "optimization", "refactor", "architecture", "performance", "concurrency",
    "kernel", "compiler", "linker", "cryptography", "vulnerability", "exploit",
    "distributed", "consensus", "replication", "sharding", "neural", "gradient"
]
MED = [
    "bug", "fix", "api", "endpoint", "database", "query", "migration",
    "authentication", "integration", "cache", "async", "thread", "socket",
    "serialization", "parsing", "algorithm", "data structure"
]
EASY = [
    "typo", "documentation", "readme", "comment", "spelling", "broken link",
    "formatting", "style", "indent", "rename", "cleanup", "minor", "trivial",
    "beginner", "good first issue", "help wanted", "simple", "easy"
]
HARD_LABELS = {
    "hard", "complex", "expert", "difficulty: hard",
    "high complexity", "needs expertise", "senior", "advanced",
    "critical", "security", "performance", "breaking change",
    "needs investigation", "deep dive", "research needed",
    "infrastructure", "scalability", "requires design"
}

EASY_LABELS = {
    "good first issue", "beginner", "easy", "difficulty: easy",
    "help wanted", "starter", "low hanging fruit", "first-timers-only",
    "trivial", "minor", "quick fix", "hacktoberfest", "up for grabs",
    "small", "beginner friendly", "easy fix", "newbie", "introductory",
    "documentation", "typo", "good-first-pr", "entry level"
}

MED_LABELS = {
    "difficulty: medium", "intermediate", "medium",
    "moderate", "some experience", "needs context",
    "contributor friendly", "help needed", "second issue",
    "needs testing", "needs review", "improvement",
    "enhancement", "refactor", "optimization"
}
def matchCount(text, term_l):
    count = 0
    for term in term_l:
        if term in text:
            count += 1
    return count

def computeScore(title, body, comment_count, labels = ""):
    title_c = title.lower()
    body_c  = body.lower()
    label_c = labels.lower()
    set = {l.strip() for l in label_c.split(",") if l.strip()}

    if set & HARD_LABELS:
        return 4.0
    if set & EASY_LABELS:
        return 0.0
    if set & MED_LABELS:
        return 1.0

    hard = matchCount(title_c, HARD)
    easy = matchCount(title_c, EASY)
    med  = matchCount(title_c, MED)

    body_words = max(len(body_c.split()), 1)
    hard_den = matchCount(body_c, HARD) / body_words * 100
    easy_den = matchCount(body_c, EASY) / body_words * 100
    med_den  = matchCount(body_c, MED)  / body_words * 100

    engagement    =  (math.log1p(comment_count) / math.log1p(20))
    length = 0.5 * (math.log1p(len(body)) / math.log1p(2000))

    score = (4.0 * hard - 2.0 * easy + 1.0 * med + 3.0 * hard_den - 1.0 * easy_den + 0.5 * med_den + engagement + length)

    if (hard + matchCount(body_c, HARD)) >= 2:
        score = max(score, 0.6)

    return score

def classify(title, body, comment_count, labels =""):
    score = computeScore(title, body, comment_count,labels)
    if score < 0.5:   return "Easy"
    elif score < 2.0: return "Medium"
    else:             return "Hard"