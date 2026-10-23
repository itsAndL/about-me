#!/usr/bin/env python3
"""Assert the rendered DOM (from `chrome --dump-dom`) against each feature's contract.

Usage: python3 check_content.py <dom.html> [feature ...]
Features: intro, projects, contact, footer (default: all).
Exits non-zero on any mismatch. The expected values mirror features/*.md.
"""
import sys
from html.parser import HTMLParser

PROJECT_URLS = [
    "https://opilote.com",
    "https://getstarted.timlead.com",
    "https://testskills.app",
    "https://humaneo.ma",
]
CONTACT_URLS = [
    "mailto:ayoub003lkebch@gmail.com",
    "https://www.linkedin.com/in/ayoublkebch",
    "https://github.com/itsAndL",
    "https://ayoublkebch.com",
]
FOOTER_URLS = ["https://github.com/itsAndL/about-me"]

FEATURES = {
    "intro": {
        "strings": [
            '<span class="monogram">AL</span>',
            "<h1>Ayoub Lkebch</h1>",
            "Full-stack product engineer. I build software for businesses — <strong>4 B2B products shipped</strong>, now building <strong>Opilote</strong>.",
            "I work with AI coding agents every day: I write the spec, review every diff, and ship small PRs.",
            '<p class="location">Casablanca, Morocco</p>',
        ],
        "counts": {"intro": 1, "lede": 1, "ai-note": 1, "location": 1},
    },
    "projects": {
        "strings": [
            '<h2 id="shipped-heading">Shipped</h2>',
            '<span class="badge">Building now</span>',
            "opilote.com", "getstarted.timlead.com", "testskills.app", "humaneo.ma",
            "GPS fleet-management SaaS I'm building end to end: Rails API, React web app, React Native app live on Google Play.",
            "Field-service platform used by 6,000+ people. I built its AI assistant and MCP server.",
            "Skills-assessment and hiring platform I led from the first commit.",
            "HR SaaS used by 7,000+ employees.",
        ],
        "counts": {"projects": 1, "project": 4, "project-name": 4, "badge": 1, "project-link": 4, "project-desc": 4},
        "links": ("project-link", PROJECT_URLS),
    },
    "contact": {
        "strings": [
            '<h2 id="contact-heading">Contact</h2>',
            ">ayoub003lkebch@gmail.com<", ">LinkedIn<", ">GitHub<", ">ayoublkebch.com<",
        ],
        "counts": {"contact": 1, "contact-link": 4},
        "links": ("contact-link", CONTACT_URLS),
    },
    "footer": {
        "strings": [
            "© 2026 Ayoub Lkebch · Built with Fredrin · ",
            ">Source on GitHub<",
        ],
        "counts": {"site-footer": 1},
    },
}


class Collect(HTMLParser):
    def __init__(self):
        super().__init__()
        self.classes = {}
        self.links = []  # (class list, href, target, rel)

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        cls = (a.get("class") or "").split()
        for c in cls:
            self.classes[c] = self.classes.get(c, 0) + 1
        if tag == "a" and a.get("href"):
            self.links.append((cls, a["href"], a.get("target"), a.get("rel")))


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    with open(sys.argv[1], encoding="utf-8") as f:
        dom = f.read()
    wanted = sys.argv[2:] or list(FEATURES)
    page = Collect()
    page.feed(dom)
    failures = 0

    def report(ok, label):
        nonlocal failures
        failures += not ok
        print(f"{'PASS' if ok else 'FAIL'}  {label}")

    for name in wanted:
        spec = FEATURES[name]
        print(f"== {name}")
        for s in spec["strings"]:
            report(s in dom, f"contains {s!r}")
        for cls, n in spec["counts"].items():
            got = page.classes.get(cls, 0)
            report(got == n, f".{cls} count {got} (want {n})")
        if "links" in spec:
            cls, urls = spec["links"]
            got = [href for c, href, _, _ in page.links if cls in c]
            report(got == urls, f".{cls} hrefs {got}")

    if set(wanted) == set(FEATURES):
        print("== all links")
        external = [l for l in page.links if not l[1].startswith("#")]
        got = [href for _, href, _, _ in external]
        want = PROJECT_URLS + CONTACT_URLS + FOOTER_URLS
        report(got == want, f"{len(got)} external/mailto hrefs match the approved list in order")
        for _, href, target, rel in external:
            if href.startswith("mailto:"):
                report(target is None, f"{href} opens in the same tab")
            else:
                report(target == "_blank" and rel == "noopener noreferrer", f"{href} target=_blank rel=noopener noreferrer")

    print(f"{'OK' if not failures else 'FAILED'}: {failures} failure(s)")
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
