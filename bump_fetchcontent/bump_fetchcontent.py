import os
import sys
from pathlib import Path

import requests
from git import Repo

from bump_fetchcontent.core import (
    find_cmake_files,
    get_latest_github_release,
    get_latest_gitlab_release,
    is_newer_version,
    parse_fetchcontent_declare_blocks,
)


def replace_versions_in_file(file: Path, changes):
    content = file.read_text()
    for _, _, _, old_url, new_url in changes:
        content = content.replace(old_url, new_url)
    file.write_text(content)

def main():
    token = os.getenv("INPUT_GITHUB_TOKEN")
    repo_dir = os.getenv("GITHUB_WORKSPACE")

    if not token:
        print("Error: github_token input is required")
        sys.exit(1)
    if not repo_dir:
        print("Error: GITHUB_WORKSPACE not set")
        sys.exit(1)

    repo = Repo(repo_dir)
    root = Path(repo_dir)

    files = find_cmake_files(root)
    if not files:
        print("No CMakeLists.txt or .cmake files found.")
        return 0

    changes_made = []
    for file in files:
        content = file.read_text()
        file_changes = []
        for block in parse_fetchcontent_declare_blocks(content):
            if "github.com" in block["url"]:
                latest = get_latest_github_release(block["url"])
            elif "gitlab.com" in block["url"]:
                latest = get_latest_gitlab_release(block["url"])
            else:
                latest = None
            if latest and is_newer_version(block["version"], latest):
                file_changes.append((
                    block["dep"],
                    block["version"],
                    latest,
                    block["url"],
                    block["url"].replace(block["version"], latest),
                ))
        if file_changes:
            replace_versions_in_file(file, file_changes)
            changes_made.extend([(file, *fc) for fc in file_changes])

    if not changes_made:
        print("No bumpable dependencies found.")
        return 0

    print("Committing changes...")
    # Configure user
    repo.git.config("user.email", "github-actions[bot]@users.noreply.github.com")
    repo.git.config("user.name", "github-actions[bot]")

    branch = f"bump-fetchcontent-{repo.head.commit.hexsha[:7]}"
    repo.git.checkout("-b", branch)
    repo.git.add(A=True)
    repo.index.commit("chore: bump FetchContent dependencies")
    origin = repo.remote("origin")
    origin.push(refspec=f"{branch}:{branch}", set_upstream=True)

    pr_lines = [
    "Automated bump of FetchContent dependencies by bump_fetchcontent GitHub Action.",
    "",
    "### Dependencies bumped:",
    ]
    for file, dep, oldv, newv, _, _ in changes_made:
        pr_lines.append(f"- **{dep}**: `{oldv}` → `{newv}` (in `{file.relative_to(root)}`)")

    pr_body = "\n".join(pr_lines)

    # Create a PR
    url = repo.remotes.origin.url
    if url.endswith(".git"):
        url = url[:-4]
    if url.startswith("git@github.com:"):
        url = url.replace("git@github.com:", "https://github.com/")

    parts = url.rstrip("/").split("/")
    if len(parts) < 2:
        print(f"Could not parse repo owner/name from {url}")
        return 1
    owner, repo_name = parts[-2], parts[-1]

    # Determine default branch name
    default_branch = None
    try:
        ref = repo.git.symbolic_ref("refs/remotes/origin/HEAD")
        default_branch = ref.strip().split("/")[-1]
    except Exception as e:
        print(f"Warning: Failed to detect default branch, defaulting to 'main': {e}")
        default_branch = "main"

    pr_data = {
        "title": "Bump FetchContent dependencies",
        "head": branch,
        "base": default_branch,
        "body": pr_body,
    }
    headers = {"Authorization": f"token {token}"}
    pr_url = f"https://api.github.com/repos/{owner}/{repo_name}/pulls"
    resp = requests.post(pr_url, json=pr_data, headers=headers)
    if resp.ok:
        print(f"Pull request created: {resp.json()['html_url']}")
        return 0
    else:
        print(f"Failed to create PR: {resp.status_code} {resp.text}")
        return 1

if __name__ == "__main__":
    sys.exit(main())

