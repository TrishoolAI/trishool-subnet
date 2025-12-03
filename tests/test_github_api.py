import time
import requests

GITHUB_TOKEN = ""

def get_latest_commit(owner, repo):
    url = f"https://api.github.com/repos/{owner}/{repo}/commits/master"
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "Python",
        "Authorization": f"Bearer {GITHUB_TOKEN}",
    }
    r = requests.get(url, headers=headers)
    r.raise_for_status()
    return r.json()['sha']


while True:
    try:
        sha = get_latest_commit("torvalds", "linux")
        print("Latest commit:", sha)
    except Exception as e:
        print("Error:", e)
    time.sleep(30)
