# bump_fetchcontent

GitHub Action that updates CMake FetchContent based dependencies.

Specifically, it does the following:
- looks through all `CMakeLists.txt` or `*.cmake` files in your repo
- searches for any [`FetchContent_Declare`](https://cmake.org/cmake/help/latest/module/FetchContent.html#command:fetchcontent_declare) calls
- checks if they use the URL style with a file ending in `.tar.gz`
- updates the url to a newer version if any

So it looks for dependencies like this:
```cmake
FetchContent_Declare(
  someLib
  URL https://github.com/user/repo/archive/refs/tags/v1.2.3.tar.gz
)
```
* Note: Only github and gitlab links are supported for now.

Of course, the URL style with a `.tar.gz` link is a very specific use case.
But that suffices for my own purposes for now.
Contributions welcome to support more cases.

## Example workflow

```yaml
name: Bump FetchContent
on:
  schedule:
    - cron: '0 0 1 * *' # run monthly on the 1st day at midnight UTC
  workflow_dispatch: # allows manual trigger
jobs:
  bump-fetchcontent:
    runs-on: ubuntu-latest
    steps:
      - uses: mehermvr/bump_fetchcontent@master
        with:
          github_token: ${{ secrets.GITHUB_TOKEN }}
          ignore_prereleases: 'true'  # default behavior
```

## Inputs
- `github_token` (required): Should be available by default. Needed for making a PR if required.
- `ignore_prereleases` (optional): Skips pre-release versions like alpha, rc, or beta. Default is "true".

## Dry run

You can dry run the changes on your repo by using the file `dry_run.py`.
It takes a single argument which is your repository git url.
It'll clone the repo into a temp folder and check for version updates if any.
