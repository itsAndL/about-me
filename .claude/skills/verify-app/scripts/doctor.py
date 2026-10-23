#!/usr/bin/env python3
"""Doctor: read-only health checks for the static About Me site.

Usage: python3 doctor.py [repo_root]
Exits non-zero when any check fails. Prints one line per check.
"""
import json
import os
import struct
import subprocess
import sys
from html.parser import HTMLParser
from urllib.parse import urlparse

VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "source", "track", "wbr"}
NU_URL = "https://validator.w3.org/nu/?out=json"
SITE_URL = "https://itsandl.github.io/about-me/"
REQUIRED_META = ["description", "theme-color", "og:type", "og:url", "og:title", "og:description",
                 "og:image", "og:image:width", "og:image:height", "og:image:alt", "og:locale",
                 "twitter:card", "twitter:title", "twitter:description", "twitter:image"]
SITE_FILES = ["favicon.svg", "favicon.ico", "apple-touch-icon.png", "og-image.png", "robots.txt", "sitemap.xml"]


class Scan(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.stack = []
        self.errors = []
        self.refs = []
        self.positive_tabindex = []
        self.meta = {}
        self.links = []
        self.jsonld = []
        self._in_jsonld = False

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "meta" and (a.get("name") or a.get("property")):
            self.meta.setdefault(a.get("name") or a.get("property"), a.get("content"))
        if tag == "link":
            self.links.append(a)
        if tag == "script" and a.get("type") == "application/ld+json":
            self._in_jsonld = True
            self.jsonld.append("")
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
        if self._in_jsonld:
            self.jsonld[-1] += data

    def handle_endtag(self, tag):
        if tag == "script":
            self._in_jsonld = False
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


def png_size(path):
    """Return (width, height) from a PNG's IHDR chunk, or None if it is not a PNG."""
    with open(path, "rb") as f:
        head = f.read(24)
    if head[:8] != b"\x89PNG\r\n\x1a\n":
        return None
    return struct.unpack(">II", head[16:24])


def main():
    root = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else ".")
    index = os.path.join(root, "index.html")
    failed = False

    def report(ok, label, detail=""):
        nonlocal failed
        failed |= not ok
        print(f"{'PASS' if ok else 'FAIL'}  {label}{(' — ' + detail) if detail else ''}")

    report(True, "python3 present", sys.version.split()[0])
    if not os.path.isfile(index):
        report(False, "index.html exists")
        sys.exit(1)
    report(True, "index.html exists")

    scan = Scan()
    with open(index, encoding="utf-8") as f:
        scan.feed(f.read())
    scan.close()

    local = [r for r in scan.refs if not urlparse(r[2]).scheme and not r[2].startswith(("#", "//"))]
    absolute = [r for r in local if r[2].startswith("/")]
    report(not absolute, "no root-absolute local paths",
           ", ".join(f"line {l}: {n}=\"{v}\"" for _, n, v, l in absolute) or f"{len(local)} local refs checked")

    missing = []
    for _, name, value, line in local:
        target = os.path.join(root, urlparse(value).path)
        if not os.path.isfile(target):
            missing.append(f"line {line}: {name}=\"{value}\"")
    report(not missing, "local refs resolve to files", ", ".join(missing) or ", ".join(sorted({r[2] for r in local})))

    report(not scan.positive_tabindex, "no positive tabindex (tab order = document order)",
           ", ".join(f"line {l}" for l in scan.positive_tabindex))

    missing_meta = [m for m in REQUIRED_META if not scan.meta.get(m)]
    rels = {l.get("rel"): l.get("href") for l in scan.links}
    missing_meta += [f"link rel={r}" for r in ("canonical", "icon", "apple-touch-icon") if r not in rels]
    report(not missing_meta, "SEO/social meta present", "missing " + ", ".join(missing_meta) if missing_meta
           else f"{len(REQUIRED_META)} meta + canonical/icon/apple-touch-icon links")

    urls = {"canonical": rels.get("canonical"), "og:url": scan.meta.get("og:url")}
    report(all(u == SITE_URL for u in urls.values()), "canonical and og:url equal the site URL",
           ", ".join(f"{k}={v}" for k, v in urls.items()))

    images = {k: scan.meta.get(k) for k in ("og:image", "twitter:image")}
    report(all(v == SITE_URL + "og-image.png" for v in images.values()), "og:image/twitter:image are absolute",
           ", ".join(f"{k}={v}" for k, v in images.items()))

    absent = [f for f in SITE_FILES if not os.path.isfile(os.path.join(root, f))]
    report(not absent, "icon, share-image and crawl files exist", "missing " + ", ".join(absent) if absent
           else ", ".join(SITE_FILES))

    og_path = os.path.join(root, "og-image.png")
    size = png_size(og_path) if os.path.isfile(og_path) else None
    report(size == (1200, 630), "og-image.png is 1200×630",
           f"{size[0]}×{size[1]}, {os.path.getsize(og_path) // 1024} KB" if size else "missing or not a PNG")

    try:
        people = [json.loads(block) for block in scan.jsonld]
        ok = any(p.get("@type") == "Person" and p.get("url") == SITE_URL for p in people)
        report(ok, "JSON-LD Person parses", f"{len(people)} block(s)" if ok else "no Person with url = site URL")
    except ValueError as e:
        report(False, "JSON-LD Person parses", str(e))

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
