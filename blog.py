"""Import only the public RSS feed; generate HTML without browser-side JavaScript."""

import argparse
import json
import re
import shutil
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from html import escape
from pathlib import Path
from urllib.request import Request, urlopen
from xml.etree.ElementTree import ParseError

import nh3
from defusedxml import ElementTree
from defusedxml.common import DefusedXmlException

ROOT = Path(__file__).resolve().parent
PUBLICATION = "https://jibrilmoinuddin.substack.com"
DOMAIN = "blog.jibrilasif.com"
MAX_FEED_BYTES = 10 * 1024 * 1024
CONTENT = "{http://purl.org/rss/1.0/modules/content/}encoded"
POST_URL = re.compile(re.escape(PUBLICATION) + r"/p/([a-z0-9][a-z0-9-]{0,199})/?$")
CLEANER = nh3.Cleaner(
    tags={"p", "br", "hr", "h1", "h2", "h3", "h4", "h5", "h6", "a", "em", "strong",
          "b", "i", "u", "s", "blockquote", "ul", "ol", "li", "pre", "code", "img",
          "figure", "figcaption", "table", "thead", "tbody", "tr", "th", "td", "sup", "sub", "span", "div"},
    clean_content_tags={"script", "style", "iframe", "object", "embed", "form", "svg", "math"},
    attributes={"a": {"href", "title"}, "img": {"src", "alt", "title"},
                "ol": {"start"}, "th": {"scope", "colspan", "rowspan"}, "td": {"colspan", "rowspan"}},
    url_schemes={"https", "http", "mailto"},
    url_relative=("rewrite_with_base", PUBLICATION + "/"),
    set_tag_attribute_values={"img": {"loading": "lazy", "decoding": "async"}},
    link_rel="noopener noreferrer",
)


def parse_feed(data: bytes) -> list[dict]:
    if len(data) > MAX_FEED_BYTES:
        raise ValueError("RSS feed exceeds the size limit")
    try:
        root = ElementTree.fromstring(data, forbid_dtd=True)
    except (ParseError, DefusedXmlException) as exc:
        raise ValueError("Invalid RSS feed") from exc
    channel = root.find("channel")
    if root.tag != "rss" or channel is None:
        raise ValueError("Expected an RSS channel")
    if channel.findtext("link", "").rstrip("/") != PUBLICATION:
        raise ValueError("Unexpected publication")
    posts = []
    for item in channel.findall("item"):
        source = item.findtext("link", "").strip()
        match = POST_URL.fullmatch(source)
        if not match:
            raise ValueError("Invalid post URL")
        title = item.findtext("title", "").strip()
        if not title:
            raise ValueError("Post has no title")
        try:
            published = parsedate_to_datetime(item.findtext("pubDate", ""))
            if published.tzinfo is None:
                raise ValueError("Post date needs a timezone")
        except (TypeError, ValueError) as exc:
            raise ValueError("Invalid publication date") from exc
        posts.append({
            "slug": match.group(1), "title": title,
            "source": PUBLICATION + "/p/" + match.group(1),
            "published": published.astimezone(timezone.utc).isoformat(),
            "html": CLEANER.clean(item.findtext(CONTENT) or item.findtext("description", "")),
        })
    return posts


def merge_posts(existing: list[dict], incoming: list[dict], excluded=()) -> list[dict]:
    # RSS is a moving window: an absent item is not proof that it was deleted.
    merged = {post["slug"]: post for post in existing + incoming if post["slug"] not in excluded}
    return sorted(merged.values(), key=lambda post: (post["published"], post["slug"]), reverse=True)


def sync_archive(path: Path, data: bytes) -> None:
    incoming = parse_feed(data)  # Validate everything before touching the last good archive.
    archive = json.loads(path.read_text()) if path.exists() else {"excluded": [], "posts": []}
    archive["posts"] = merge_posts(archive["posts"], incoming, archive["excluded"])
    path.parent.mkdir(parents=True, exist_ok=True)
    pending = path.with_suffix(".tmp")
    pending.write_text(json.dumps(archive, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    pending.replace(path)


def page(title: str, body: str, canonical: str, description: str) -> str:
    return f'''<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'self'; font-src 'self'; img-src https:; base-uri 'none'; form-action 'none'">
  <meta name="referrer" content="strict-origin-when-cross-origin">
  <title>{escape(title)} — Jibril Asif</title>
  <meta name="description" content="{escape(description, quote=True)}">
  <link rel="canonical" href="{escape(canonical, quote=True)}">
  <link rel="alternate" type="application/rss+xml" title="Jibril’s Substack" href="{PUBLICATION}/feed">
  <link rel="preload" href="/fonts/reckless-standard-m-regular.woff2" as="font" type="font/woff2" crossorigin>
  <link rel="stylesheet" href="/style.css">
</head>
<body>
  <main>
    {body}
    <footer><a href="https://jibrilasif.com/">Home</a><a href="{PUBLICATION}/subscribe">Subscribe on Substack</a></footer>
  </main>
</body>
</html>
'''


def build_site(posts: list[dict], output: Path) -> None:
    rendered = []
    for post in merge_posts([], posts):
        if not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,199}", post["slug"]):
            raise ValueError("Invalid archived slug")
        if post["source"] != PUBLICATION + "/p/" + post["slug"]:
            raise ValueError("Invalid archived source")
        date = datetime.fromisoformat(post["published"])
        stamp = f'<time datetime="{date:%Y-%m-%d}">{date:%B} {date.day}, {date:%Y}</time>'
        title = escape(post["title"])
        article = f'''<nav aria-label="Blog navigation"><a href="/">← All writing</a></nav>
    <article>
      <header><h1>{title}</h1><p class="date">{stamp}</p></header>
      <div class="prose">{CLEANER.clean(post["html"])}</div>
      <p class="source"><a href="{escape(post["source"], quote=True)}">Originally published on Substack</a></p>
    </article>'''
        rendered.append((post, stamp, page(post["title"], article, post["source"], post["title"])))

    output.mkdir(parents=True, exist_ok=True)
    # The output directory is dedicated to generated files. Remove only stale article pages.
    if (output / "p").exists():
        shutil.rmtree(output / "p")
    rows = []
    for post, stamp, html in rendered:
        destination = output / "p" / post["slug"]
        destination.mkdir(parents=True)
        (destination / "index.html").write_text(html, encoding="utf-8")
        rows.append(f'<li><a href="/p/{post["slug"]}/">{escape(post["title"])}</a>{stamp}</li>')
    listing = '<ul class="posts">' + "".join(rows) + "</ul>" if rows else '<p>Nothing here yet.</p>'
    index = f'<header><h1>Writing</h1><p>By <a href="https://jibrilasif.com/">Jibril Asif</a>.</p></header>{listing}'
    (output / "index.html").write_text(page("Writing", index, f"https://{DOMAIN}/", "Writing by Jibril Asif."), encoding="utf-8")
    missing = '<h1>Page not found</h1><p><a href="/">Back to writing</a>.</p>'
    (output / "404.html").write_text(page("Page not found", missing, f"https://{DOMAIN}/", "Page not found."), encoding="utf-8")
    (output / "CNAME").write_text(DOMAIN + "\n")
    (output / ".nojekyll").touch()
    shutil.copyfile(ROOT / "static/style.css", output / "style.css")
    shutil.copytree(ROOT / "static/fonts", output / "fonts", dirs_exist_ok=True)


def fetch_feed() -> bytes:
    request = Request(PUBLICATION + "/feed", headers={"User-Agent": "JibrilBlog/1.0 (blog.jibrilasif.com)", "Accept": "application/rss+xml"})
    with urlopen(request, timeout=30) as response:
        if response.url.rstrip("/") != PUBLICATION + "/feed":
            raise ValueError("Unexpected RSS redirect")
        return response.read(MAX_FEED_BYTES + 1)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["sync", "build"])
    parser.add_argument("--output", type=Path, default=ROOT / "_site")
    args = parser.parse_args()
    archive_path = ROOT / "data/posts.json"
    if args.command == "sync":
        sync_archive(archive_path, fetch_feed())
    else:
        archive = json.loads(archive_path.read_text())
        build_site(merge_posts([], archive["posts"], archive["excluded"]), args.output)


if __name__ == "__main__":
    main()
