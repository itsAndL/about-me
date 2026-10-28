#!/usr/bin/env python3
"""Assert the rendered DOM (from `chrome --dump-dom`) or the exported out/index.html against
each feature's contract.

Usage: python3 check_content.py <dom.html> [feature ...]
Features: intro, projects, contact, footer (default: all).
Exits non-zero on any mismatch. The expected values mirror features/*.md.
"""
import html
import sys
from html.parser import HTMLParser

PROJECT_URLS = [
    "https://opilote.com",
    "https://getstarted.timlead.com",
    "https://testskills.app",
    "https://humaneo.ma",
]
CONTACT_URLS = [
    "mailto:lkebch.ayoub@gmail.com",
    "https://www.linkedin.com/in/ayoublkebch",
    "https://github.com/itsAndL",
    "https://ayoublkebch.com",
]
FOOTER_URLS = ["https://github.com/itsAndL/about-me"]
VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "source", "track", "wbr"}

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
            ">lkebch.ayoub@gmail.com<", ">LinkedIn<", ">GitHub<", ">ayoublkebch.com<",
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
        self.body_first = None  # (tag, class, href) of the first visible element inside <body>
        self._in_body = False
        self._hidden_depth = 0  # >0 while inside a `hidden` element (Next.js injects one first)
        self._anchor = None  # [target, saw aria-hidden ↗, saw new-tab note] for the open <a>
        self._span = None
        self.anchor_extras = []  # (href, target, has aria-hidden arrow, has new-tab note)

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        cls = (a.get("class") or "").split()
        for c in cls:
            self.classes[c] = self.classes.get(c, 0) + 1
        if self._hidden_depth:
            if tag not in VOID:
                self._hidden_depth += 1
        elif "hidden" in a and self._in_body and tag not in VOID:
            self._hidden_depth = 1
        elif self._in_body and self.body_first is None:
            self.body_first = (tag, a.get("class"), a.get("href"))
        if tag == "body":
            self._in_body = True
        if tag == "a" and a.get("href"):
            self.links.append((cls, a["href"], a.get("target"), a.get("rel")))
            self._anchor = {"href": a["href"], "target": a.get("target"), "arrow": False, "note": False}
        if tag == "span" and self._anchor is not None:
            self._span = "arrow" if a.get("aria-hidden") == "true" else "note" if "visually-hidden" in cls else None

    def handle_data(self, data):
        if self._anchor is None or self._span is None:
            return
        if self._span == "arrow" and data.strip() == "↗":
            self._anchor["arrow"] = True
        if self._span == "note" and data == " (opens in a new tab)":
            self._anchor["note"] = True

    def handle_endtag(self, tag):
        if self._hidden_depth and tag not in VOID:
            self._hidden_depth -= 1
        if tag == "span":
            self._span = None
        if tag == "a" and self._anchor is not None:
            self.anchor_extras.append(self._anchor)
            self._anchor = None


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    with open(sys.argv[1], encoding="utf-8") as f:
        raw = f.read()
    # The exported HTML escapes text (React writes ' as &#x27;); compare strings as rendered.
    dom = html.unescape(raw)
    wanted = sys.argv[2:] or list(FEATURES)
    page = Collect()
    page.feed(raw)
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
        if name == "intro":
            report(page.body_first == ("a", "visually-hidden-focusable", "#main"),
                   f"first element in body is the skip link (got {page.body_first})")
        if name == "projects":
            arrows = [x["href"] for x in page.anchor_extras if x["arrow"]]
            report(arrows == PROJECT_URLS, "each .project-link has an aria-hidden ↗")
            report('<h3 class="project-name">Opilote <span class="badge">Building now</span></h3>' in dom,
                   ".badge sits inside Opilote's .project-name")
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
        notes = {x["href"]: x["note"] for x in page.anchor_extras}
        for _, href, target, rel in external:
            if href.startswith("mailto:"):
                report(target is None, f"{href} opens in the same tab")
            else:
                report(target == "_blank" and rel == "noopener noreferrer" and notes.get(href),
                       f"{href} target=_blank rel=noopener noreferrer + hidden '(opens in a new tab)'")

    print(f"{'OK' if not failures else 'FAILED'}: {failures} failure(s)")
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
