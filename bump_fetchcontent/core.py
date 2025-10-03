import re

import requests
from packaging.version import InvalidVersion, parse


def parse_version_safe(ver_str: str):
    try:
        return parse(ver_str)
    except InvalidVersion:
        # fallback: strip anything after '-'
        base_ver = ver_str.split('-')[0]
        return parse(base_ver)

def is_newer_version(old_ver: str, new_ver: str) -> bool:
    try:
        old_v = parse_version_safe(old_ver.lstrip("v"))
        new_v = parse_version_safe(new_ver.lstrip("v"))
        return new_v > old_v
    except:
        # fallback
        return new_ver != old_ver

def find_cmake_files(root):
    return [
        p for p in root.rglob("*")
        if p.is_file() and (p.name == "CMakeLists.txt" or p.suffix == ".cmake")
    ]

def parse_fetchcontent_declare_blocks(text):
    pat = re.compile(
        r"FetchContent_Declare\(\s*([A-Za-z0-9_]+)\s+([^\)]*?URL\s+([^\s\)]+\.tar\.gz))",
        re.DOTALL)
    for m in pat.finditer(text):
        dep = m.group(1)
        url = m.group(3)
        version = re.search(r'(v?[0-9]+(?:\.[0-9]+){1,3})', url)
        if version:
            yield {
                "dep": dep,
                "url": url,
                "version": version.group(1)
            }
            
def get_newest_version_from_list(entries):
    newest = None
    for entry in entries:
        tag = entry.get("tag_name") or entry.get("name")
        if not tag:
            continue
        vstr = tag.lstrip("v")
        try:
            ver_obj = parse(vstr)
        except:
            continue
        if newest is None or ver_obj > parse(newest.lstrip("v")):
            newest = tag
    return newest

def get_latest_github_release(url):
    m = re.match(
        r".*github.com/([^/]+)/([^/]+)/archive/refs/tags/(v?[\d\.]+)\.tar\.gz", url)
    if not m:
        return None
    org, repo, _ = m.groups()
    api_url = f"https://api.github.com/repos/{org}/{repo}/tags"
    r = requests.get(api_url, timeout=10)
    if r.ok:
        tags = r.json()
        if not tags:
            return None
        return get_newest_version_from_list(tags)
    return None

def get_latest_gitlab_release(url):
    m = re.match(
        r".*gitlab.com/([^/]+)/([^/]+)/-/(?:archive|releases)/([\d\.]+)/", url)
    if not m:
        return None
    org, repo, _ = m.groups()
    api_url = f"https://gitlab.com/api/v4/projects/{org}%2F{repo}/releases"
    r = requests.get(api_url, timeout=10)
    if r.ok:
        releases = r.json()
        if not releases:
            return None
        return get_newest_version_from_list(releases)
    return None

