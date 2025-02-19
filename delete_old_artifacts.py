import requests
import os
import sys

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
if not GITHUB_TOKEN:
    msg = """Github token must be present in GITHUB_TOKEN environment variable.
Go to https://github.com/settings/personal-access-tokens to create one,
or request help from Martin if he's free at this very moment."""

    print(msg, file = sys.stderr)
    raise KeyError(msg)

OWNER = "PALMS-MLAB"
REPO = "PALMS-Simulator"

def get_artifacts():
    url = f"https://api.github.com/repos/{OWNER}/{REPO}/actions/artifacts"
    print(f'Getting artifacts from {url}')
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json"
    }
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    return response.json()

def delete_artifact(artifact_id):
    url = f"https://api.github.com/repos/{OWNER}/{REPO}/actions/artifacts/{artifact_id}"
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json"
    }
    response = requests.delete(url, headers=headers)
    response.raise_for_status()

def main():
    artifacts = get_artifacts()
    for artifact in artifacts.get("artifacts", []):
        artifact_id = artifact["id"]
        print(f"Deleting artifact {artifact['name']} (ID: {artifact_id})")
        delete_artifact(artifact_id)

if __name__ == "__main__":
    main()
