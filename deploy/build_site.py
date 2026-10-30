#!/usr/bin/env python3
"""Build the deployable site from dashboard/crack_signal_readout.html.

Output goes to deploy/site/. Differences from the source file:
  - the links to the paper PDF are removed (the PDF is not hosted),
  - a robots meta tag and robots.txt ask search engines not to index the site,
"""
import pathlib

root = pathlib.Path(__file__).resolve().parent
src = (root.parent / "dashboard" / "crack_signal_readout.html").read_text(encoding="utf-8")


def cut(text, old, new=""):
    if text.count(old) != 1:
        raise SystemExit(f"Expected exactly one match for: {old[:60]!r} (found {text.count(old)})")
    return text.replace(old, new)


out = src
out = cut(out, '      <a class="btn" href="../paper/IN939_LPBF_paper.pdf"><span>Read<span class="hs"> the</span> paper</span></a>\n')
out = cut(out, '      <a class="l" href="../paper/IN939_LPBF_paper.pdf">Read the full paper (PDF)</a>\n')
out = cut(out, '<meta name="description"', '<meta name="robots" content="noindex, nofollow">\n<meta name="description"')

site = root / "site"
site.mkdir(exist_ok=True)
(site / "index.html").write_text(out, encoding="utf-8")
(site / "robots.txt").write_text("User-agent: *\nDisallow: /\n", encoding="utf-8")
print(f"Built {site / 'index.html'} ({len(out):,} bytes)")
