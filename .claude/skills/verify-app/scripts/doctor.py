#!/usr/bin/env python3
"""Doctor: read-only health checks for the About Me Next.js static export.

Usage: python3 doctor.py [repo_root] [--served http://127.0.0.1:<port>]
Expects `npm run build` to have written out/. With --served it also fetches every local
asset the page references from that server (which serves out/ under /about-me/).
Exits non-zero when any check fails. Prints one line per check.
"""
import json
import os
import re
import shutil
import struct
import subprocess
import sys
import urllib.error
import urllib.request
from html.parser import HTMLParser
from urllib.parse import urlparse

BASE_PATH = "/about-me/"
VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "source", "track", "wbr"}
NU_URL = "https://validator.w3.org/nu/?out=json"
MIN_NODE = (20, 9)
SITE_URL = "https://itsandl.github.io/about-me/"
# Static files in public/ plus the app/ metadata file conventions (icons, share images).
PUBLIC_FILES = [".nojekyll", "robots.txt", "sitemap.xml", "icon.svg", "icon.ico", "apple-icon.png",
                "opengraph-image.png", "twitter-image.png"]
OG_SIZE = (1200, 630)


class Scan(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.stack = []
        self.errors = []
        self.refs = []
        self.positive_tabindex = []
        self.meta = {}  # name/property → [content, ...]
        self.links = []  # (rel, href)
        self.json_ld = []
        self._in_json_ld = False

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "meta" and (a.get("name") or a.get("property")):
            self.meta.setdefault(a.get("name") or a.get("property"), []).append(a.get("content") or "")
        if tag == "link" and a.get("rel"):
            self.links.append((a["rel"], a.get("href") or ""))
        if tag == "script" and a.get("type") == "application/ld+json":
            self._in_json_ld = True
            self.json_ld.append("")
        for name, value in attrs:
            if name in ("href", "src") and value is not None:
                self.refs.append((tag, name, value, self.getpos()[0]))
            if name == "tabindex" and value and value.strip().lstrip("+").isdigit() and int(value) > 0:
                self.positive_tabindex.append(self.getpos()[0])
        if tag not in VOID:
            self.stack.append((tag, self.getpos()[0]))

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if tag not in VOID:
            self.stack.pop()

    def handle_data(self, data):
        if self._in_json_ld:
            self.json_ld[-1] += data

    def handle_endtag(self, tag):
        if tag == "script":
            self._in_json_ld = False
        if tag in VOID:
            return
        if not self.stack or self.stack[-1][0] != tag:
            open_tags = [t for t, _ in self.stack]
            if tag in open_tags:
                # Pop through the unclosed children so one mistake reports once.
                while self.stack[-1][0] != tag:
                    t, line = self.stack.pop()
                    self.errors.append(f"line {line}: <{t}> not closed before </{tag}>")
                self.stack.pop()
            else:
                self.errors.append(f"line {self.getpos()[0]}: stray </{tag}>")
            return
        self.stack.pop()


def run(cmd, cwd):
    """Return (exit code, last lines of combined output)."""
    proc = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, check=False)
    tail = (proc.stdout + proc.stderr).strip().splitlines()[-5:]
    return proc.returncode, " | ".join(tail)


def node_version():
    try:
        out = subprocess.run(["node", "--version"], capture_output=True, text=True, check=True).stdout
    except (OSError, subprocess.CalledProcessError):
        return None
    return tuple(int(p) for p in out.strip().lstrip("v").split(".")[:2])


def nu_check(path):
    """Return (reachable, [error messages]) from the W3C Nu checker."""
    try:
        out = subprocess.run(
            ["curl", "-s", "--max-time", "20", "-H", "Content-Type: text/html; charset=utf-8",
             "-H", "User-Agent: verify-app-doctor", "--data-binary", f"@{path}", NU_URL],
            capture_output=True, text=True, check=False,
        ).stdout
        messages = json.loads(out)["messages"]
    except (ValueError, KeyError, OSError):
        return False, []
    if any(m.get("type") == "non-document-error" for m in messages):
        return False, []  # the checker could not read the input, so nothing was validated
    return True, [f"line {m.get('lastLine', '?')}: {m['message']}" for m in messages if m.get("type") == "error"]


def http_status(url):
    try:
        with urllib.request.urlopen(url, timeout=10) as resp:
            return resp.status
    except urllib.error.HTTPError as e:
        return e.code
    except (urllib.error.URLError, OSError) as e:
        return str(e)


def png_size(path):
    """Return (width, height) from a PNG's IHDR chunk, or None if it is not a PNG."""
    with open(path, "rb") as f:
        head = f.read(24)
    if head[:8] != b"\x89PNG\r\n\x1a\n":
        return None
    return struct.unpack(">II", head[16:24])


def check_metadata(scan, out, served, report):
    """SEO/social head: required tags, absolute URLs under SITE_URL, share image and crawl files."""
    meta = scan.meta
    required = ["description", "og:title", "og:description", "og:url", "og:type", "og:image",
                "og:image:alt", "twitter:card", "twitter:title", "twitter:description", "twitter:image",
                "twitter:image:alt"]
    absent = [k for k in required if not meta.get(k)]
    report(not absent, "metadata: required meta tags present", "missing " + ", ".join(absent) if absent
           else f"{len(required)} tags")

    report(meta.get("twitter:card") == ["summary_large_image"], "metadata: twitter:card is summary_large_image",
           str(meta.get("twitter:card")))
    themes = meta.get("theme-color", [])
    report(len(themes) == 2, "metadata: two theme-color metas (light + dark)", ", ".join(themes))

    canonical = [href for rel, href in scan.links if rel == "canonical"]
    og_url = meta.get("og:url", [])
    report(canonical == [SITE_URL] and og_url == [SITE_URL], f"metadata: canonical == og:url == {SITE_URL}",
           f"canonical={canonical} og:url={og_url}")

    for key in ("og:image", "twitter:image"):
        for url in meta.get(key, []):
            if not url.startswith(SITE_URL):
                report(False, f"metadata: {key} is under {SITE_URL}", url)
                continue
            path = urlparse(url).path
            file = os.path.join(out, path[len(BASE_PATH):])
            ok = os.path.isfile(file)
            size = png_size(file) if ok else None
            report(ok and size == OG_SIZE, f"metadata: {key} resolves to a {OG_SIZE[0]}×{OG_SIZE[1]} file in out/",
                   f"{path} → {size or 'missing'}")
            if served:
                status = http_status(served + path)
                report(status == 200, f"metadata: {key} returns 200 when served", f"{path} → {status}")

    icons = [href for rel, href in scan.links if rel in ("icon", "apple-touch-icon")]
    report(any(rel == "icon" for rel, _ in scan.links) and any(rel == "apple-touch-icon" for rel, _ in scan.links),
           "metadata: icon and apple-touch-icon links present", ", ".join(icons))

    people = []
    for raw in scan.json_ld:
        try:
            data = json.loads(raw)
        except ValueError as e:
            report(False, "metadata: JSON-LD parses", str(e))
            continue
        if data.get("@type") == "Person":
            people.append(data)
    report(len(people) == 1 and people[0].get("url") == SITE_URL, "metadata: one JSON-LD Person with url " + SITE_URL,
           f"{len(people)} Person block(s)")

    for name in ("robots.txt", "sitemap.xml"):
        file = os.path.join(out, name)
        text = open(file, encoding="utf-8").read() if os.path.isfile(file) else ""
        expected = SITE_URL + "sitemap.xml" if name == "robots.txt" else SITE_URL
        report(expected in text, f"metadata: {name} references {expected}")
        if served:
            status = http_status(served + BASE_PATH + name)
            report(status == 200, f"metadata: {BASE_PATH}{name} returns 200 when served", str(status))


def main():
    args = sys.argv[1:]
    served = None
    if "--served" in args:
        i = args.index("--served")
        if i + 1 >= len(args):
            sys.exit("usage: doctor.py [repo_root] [--served http://127.0.0.1:<port>]")
        served = args[i + 1].rstrip("/")
        del args[i:i + 2]
    root = os.path.abspath(args[0] if args else ".")
    out = os.path.join(root, "out")
    index = os.path.join(out, "index.html")
    failed = False

    def report(ok, label, detail=""):
        nonlocal failed
        failed |= not ok
        print(f"{'PASS' if ok else 'FAIL'}  {label}{(' — ' + detail) if detail else ''}")

    version = node_version()
    report(version is not None and version >= MIN_NODE, f"node >= {'.'.join(map(str, MIN_NODE))}",
           ".".join(map(str, version)) if version else "node not found")
    report(shutil.which("npm") is not None, "npm present")

    code, tail = run(["npx", "tsc", "--noEmit"], root)
    report(code == 0, "npx tsc --noEmit", tail if code else "")
    code, tail = run(["npm", "run", "lint", "--silent"], root)
    report(code == 0, "npm run lint", tail if code else "")

    if not os.path.isfile(index):
        report(False, "out/index.html exists", "run `npm run build` first")
        sys.exit(1)
    report(True, "out/index.html exists")

    with open(index, encoding="utf-8") as f:
        html = f.read()
    scan = Scan()
    scan.feed(html)
    scan.close()

    # Catches inline scripts and payloads too, not just href/src attributes.
    rooted = re.findall(r'(?<!/about-me)/_next/[^"\'\s]*', html)
    report(not rooted, "zero root-absolute /_next references", ", ".join(sorted(set(rooted))[:5]))

    local = [r for r in scan.refs if not urlparse(r[2]).scheme and not r[2].startswith(("#", "//"))]
    outside = [r for r in local if not r[2].startswith(BASE_PATH)]
    report(not outside, f"every local href/src starts with {BASE_PATH}",
           ", ".join(f"{n}=\"{v}\"" for _, n, v, _ in outside) or f"{len(local)} local refs checked")

    missing = []
    for _, name, value, _ in local:
        path = urlparse(value).path
        if not path.startswith(BASE_PATH):
            continue
        target = os.path.join(out, path[len(BASE_PATH):])
        if path.endswith("/"):
            target = os.path.join(target, "index.html")
        if not os.path.isfile(target):
            missing.append(f"{name}=\"{value}\"")
    report(not missing, "local refs resolve to files in out/", ", ".join(missing) or f"{len(local)} files")

    if served:
        bad = []
        for _, _, value, _ in local:
            status = http_status(served + value)
            if status != 200:
                bad.append(f"{value} → {status}")
        report(not bad, f"every referenced asset returns 200 from {served}", ", ".join(bad) or f"{len(local)} × 200")

    absent = [f for f in PUBLIC_FILES if not os.path.isfile(os.path.join(out, f))]
    report(not absent, "public/ assets ship in out/", "missing " + ", ".join(absent) if absent
           else ", ".join(PUBLIC_FILES))

    check_metadata(scan, out, served, report)

    report(not scan.positive_tabindex, "no positive tabindex (tab order = document order)",
           ", ".join(f"line {l}" for l in scan.positive_tabindex))

    unclosed = scan.errors + [f"line {line}: <{t}> never closed" for t, line in scan.stack]
    report(not unclosed, "HTML well-formed (local html.parser)", "; ".join(unclosed))

    reachable, nu_errors = nu_check(index)
    if reachable:
        report(not nu_errors, "W3C Nu checker: no errors", "; ".join(nu_errors))
    else:
        print("SKIP  W3C Nu checker unreachable or could not read the file — relying on the local parser above")

    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
