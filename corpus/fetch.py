#!/usr/bin/env python3
"""Download the corpus listed in corpus/sources.yaml, politely, and record it.

    python corpus/fetch.py                       # download what is missing
    python corpus/fetch.py --force               # download everything again
    python corpus/fetch.py --verify              # re-hash local files against MANIFEST.md
    python corpus/fetch.py --list URL            # list the documents linked from an index page

Writes:
    corpus/raw/<file>         the documents (gitignored: never commit someone else's PDFs)
    corpus/raw/_index.json    file -> doc_version, superseded; the indexer reads this
    corpus/MANIFEST.md        URL, size and SHA-256 per document (commit this)

Rules this script follows so 40 teams do not hammer one university website:
one request at a time, a pause between requests, a clear User-Agent, each file
downloaded once and then reused.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import time
from html.parser import HTMLParser
from io import BytesIO
from pathlib import Path
from urllib.parse import quote, urljoin, urlsplit

import httpx
import yaml
from pypdf import PdfReader

HERE = Path(__file__).resolve().parent
RAW = HERE / "raw"
SOURCES = HERE / "sources.yaml"
MANIFEST = HERE / "MANIFEST.md"
USER_AGENT = "RAHBAR-coursework-fetcher/1.0 (CS4032 student project; one request at a time)"
PAUSE_SECONDS = 2.0
DRIVE_VIEW = re.compile(r"https?://drive\.google\.com/file/d/([^/?#]+)")


def normalise(url: str) -> str:
    """Encode spaces and other unsafe characters, and turn Drive viewer links into
    direct downloads. Already-encoded %XX sequences are left alone."""
    match = DRIVE_VIEW.match(url)
    if match:
        return f"https://drive.google.com/uc?export=download&id={match.group(1)}"
    return quote(url, safe=":/?&=%#+,;@!$'()*~")


def slug(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")[:80] or "document"


def get(client: httpx.Client, url: str, attempts: int = 3) -> httpx.Response:
    for attempt in range(1, attempts + 1):
        try:
            response = client.get(url)
            if response.status_code < 500:
                return response
            reason = f"HTTP {response.status_code}"
        except httpx.TransportError as exc:
            reason = type(exc).__name__
        if attempt < attempts:
            wait = PAUSE_SECONDS * 2 ** attempt
            print(f"    {reason}; retrying in {wait:.0f}s ({attempt}/{attempts - 1})")
            time.sleep(wait)
    raise RuntimeError(f"gave up after {attempts} attempts: {reason}")


def load_sources() -> list[dict]:
    data = yaml.safe_load(SOURCES.read_text(encoding="utf-8"))
    docs = data["documents"]
    if not docs or len({slug(doc["name"]) for doc in docs}) != len(docs):
        raise ValueError("sources.yaml requires a nonempty set of unique document names")
    return docs


def fetch(force: bool, verify_only: bool = False) -> int:
    RAW.mkdir(exist_ok=True)
    entries = []
    with httpx.Client(headers={"User-Agent": USER_AGENT}, follow_redirects=True,
                      timeout=httpx.Timeout(60.0, connect=15.0)) as client:
        for doc in load_sources():
            url = normalise(doc["url"])
            path = RAW / (slug(doc["name"]) + ".pdf")
            if verify_only or (path.is_file() and not force):
                body = path.read_bytes()
            else:
                try:
                    response = get(client, url)
                    response.raise_for_status()
                    body = response.content
                finally:
                    time.sleep(PAUSE_SECONDS)
            digest = hashlib.sha256(body).hexdigest()
            if digest != doc["sha256"] or not body.startswith(b"%PDF-"):
                raise ValueError(f"{path.name}: expected pinned PDF SHA-256 {doc['sha256']}, got {digest}")
            pages = len(PdfReader(BytesIO(body)).pages)
            if pages != doc["pages"]:
                raise ValueError(f"{path.name}: expected {doc['pages']} pages, got {pages}")
            if not verify_only and (force or not path.is_file()):
                pending = path.with_suffix(".part")
                pending.write_bytes(body)
                pending.replace(path)
            print(f"  verified {path.name} ({pages} pages)")
            entries.append({**doc, "url": url, "file": path.name, "bytes": len(body)})

    manifest = render_manifest(entries)
    if verify_only:
        if MANIFEST.read_text(encoding="utf-8") != manifest:
            raise ValueError("MANIFEST.md differs from the verified corpus")
        local_index = json.loads((RAW / "_index.json").read_text(encoding="utf-8"))
        if local_index != entries:
            raise ValueError("_index.json differs from the verified corpus; run fetch again")
    else:
        pending = RAW / "_index.tmp"
        pending.write_text(json.dumps(entries, indent=2) + "\n", encoding="utf-8")
        pending.replace(RAW / "_index.json")
        MANIFEST.write_text(manifest, encoding="utf-8")
    print(f"{len(entries)} verified PDFs, {sum(e['pages'] for e in entries)} pages")
    return 0


def render_manifest(entries: list[dict]) -> str:
    lines = [
        "# Corpus manifest",
        "",
        "Generated by `python corpus/fetch.py`. Public FAST-NUCES publications remain "
        "in the ignored `corpus/raw/` directory. Use `--verify` to check this snapshot.",
        "",
        "| Document | Version | Superseded | File | Pages | Bytes | SHA-256 | URL | Notes |",
        "| --- | --- | --- | --- | ---: | ---: | --- | --- | --- |",
    ]
    for e in entries:
        lines.append(f"| {e['name']} | {e['doc_version']} | {'yes' if e['superseded'] else 'no'} "
                     f"| `{e['file']}` | {e['pages']} | {e['bytes']:,} | `{e['sha256']}` "
                     f"| <{e['url']}> | {e['notes']} |")
    return "\n".join(lines) + "\n"


class _Links(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.links: list[tuple[str, str]] = []
        self._href: str | None = None
        self._text: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "a":
            self._href = dict(attrs).get("href")
            self._text = []

    def handle_data(self, data: str) -> None:
        if self._href is not None:
            self._text.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag == "a" and self._href:
            self.links.append((self._href, " ".join("".join(self._text).split())))
            self._href = None


def list_documents(index_url: str) -> int:
    """Print the PDF and Google Drive links on an index page, ready to paste into
    sources.yaml. Downloads nothing but the page itself."""
    with httpx.Client(headers={"User-Agent": USER_AGENT}, follow_redirects=True,
                      timeout=30.0) as client:
        page = get(client, index_url)
    parser = _Links()
    parser.feed(page.text)
    seen = set()
    for href, text in parser.links:
        url = urljoin(index_url, href)
        is_doc = urlsplit(url).path.lower().endswith(".pdf") or DRIVE_VIEW.match(url)
        if is_doc and url not in seen:
            seen.add(url)
            name = text or Path(urlsplit(url).path).name
            print(f"  - name: {json.dumps(name)}\n    url: {json.dumps(url)}")
    print(f"\n{len(seen)} document links on {index_url}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--force", action="store_true", help="download everything again")
    group.add_argument("--verify", action="store_true", help="check local files against MANIFEST.md")
    group.add_argument("--list", metavar="URL", help="list document links on an index page")
    args = parser.parse_args()
    if args.list:
        return list_documents(args.list)
    try:
        return fetch(force=args.force, verify_only=args.verify)
    except (OSError, ValueError, httpx.HTTPError, RuntimeError) as exc:
        parser.exit(1, f"corpus verification failed: {exc}\n")


if __name__ == "__main__":
    sys.exit(main())
