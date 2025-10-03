import tempfile
from pathlib import Path

import typer
from git import Repo

from bump_fetchcontent.core import *

app = typer.Typer()

@app.command()
def dry_run(
    repo_url: str = typer.Argument(..., help="GitHub repo URL to clone and scan"),
):
    with tempfile.TemporaryDirectory() as tmpdir:
        print(f"Cloning {repo_url} into temporary directory {tmpdir} ...")
        Repo.clone_from(repo_url, tmpdir, depth=1)
        print("Clone complete. Scanning CMake files...\n")
        root = Path(tmpdir)

        files = find_cmake_files(root)
        if not files:
            print("No CMakeLists.txt or .cmake files found!")
            return

        any_changes = False
        for file in files:
            content = file.read_text()
            changes = []
            for block in parse_fetchcontent_declare_blocks(content):
                if "github.com" in block["url"]:
                    latest = get_latest_github_release(block["url"])
                elif "gitlab.com" in block["url"]:
                    latest = get_latest_gitlab_release(block["url"])
                else:
                    latest = None
                if latest and is_newer_version(block["version"], latest):
                    changes.append(
                        (
                            block["dep"],
                            block["version"],
                            latest,
                            block["url"],
                            block["url"].replace(block["version"], latest),
                        )
                    )
            if changes:
                any_changes = True
                print(f"\n{file.relative_to(root)}:")
                for dep, oldv, newv, old, new in changes:
                    print(f"  {dep}: {oldv} -> {newv}")
                    print(f"    {old}\n -> {new}")
        if not any_changes:
            print("No bumpable dependencies found.")
        else:
            print("\nDRY RUN only: no files were modified.")

if __name__ == "__main__":
    app()

