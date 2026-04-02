import requests
import pandas as pd

import os
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")

def scrapeIssues(repo_url):
    url = repo_url.strip()
    parts = url.rstrip("/").split("/")
    owner = parts[-2]
    repo = parts[-1]

    issues = []
    page = 1
    while len(issues) < 3000:
        url = f"https://api.github.com/repos/{owner}/{repo}/issues"
        params = {"state":"open","per_page":100,"page":page}
        header = {"Authorization": f"token {GITHUB_TOKEN}"}
        response = requests.get(url,headers=header,params=params)
        print(f"GITHUB STATUS: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
        else :
            print(f"ERROR : {response.status_code}")
            break
        for issue in data:
            if "pull_request" in issue:
                continue
            issues.append({
                "title": issue["title"],
                "body": issue["body"] or "",
                "labels": ", ".join([l["name"] for l in issue["labels"]]),
                "comment_count": issue["comments"],
                "last_updated": issue["updated_at"][:10],
                "url": issue["html_url"],
                "number": issue["number"]
            })
        page+=1
        if len(data) < 100:
            break
    return issues

if __name__ == "__main__":
    issues = scrapeIssues("https://github.com/numpy/numpy")


