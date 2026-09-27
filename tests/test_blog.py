import json
import tempfile
import unittest
from pathlib import Path

import blog

PUBLICATION = "https://jibrilmoinuddin.substack.com"


def feed(body="<p>Full article, not the summary.</p>", slug="hello", title="Hello", date="Fri, 30 Aug 2024 02:52:03 GMT"):
    return f'''<rss version="2.0" xmlns:content="http://purl.org/rss/1.0/modules/content/">
      <channel><title>Jibril’s Substack</title><link>{PUBLICATION}</link>
      <item><title><![CDATA[{title}]]></title><link>{PUBLICATION}/p/{slug}</link>
      <pubDate>{date}</pubDate><description>Short summary.</description>
      <content:encoded><![CDATA[{body}]]></content:encoded></item></channel></rss>'''.encode()


class ImportTests(unittest.TestCase):
    def test_reads_full_article_and_normalizes_date(self):
        post, = blog.parse_feed(feed())
        self.assertEqual(post["slug"], "hello")
        self.assertIn("Full article", post["html"])
        self.assertNotIn("Short summary", post["html"])
        self.assertEqual(post["published"], "2024-08-30T02:52:03+00:00")

    def test_sanitizes_active_html_and_keeps_images_and_formatting(self):
        body = '''<script>alert(1)</script><iframe src="https://evil.test">hidden</iframe>
          <p onclick="alert(2)" style="position:fixed">Safe <em>words</em></p>
          <a href="javascript:alert(3)">bad link</a><a href="/subscribe">Subscribe</a>
          <img src="https://images.example/photo.jpg" onerror="alert(4)" alt="Photo">
          <svg onload="alert(5)"></svg><form><input name="password"></form>'''
        html = blog.parse_feed(feed(body))[0]["html"]
        for forbidden in ("<script", "<iframe", "onclick", "onerror", "javascript:", "<svg", "<form", "style=", "alert("):
            self.assertNotIn(forbidden, html)
        self.assertIn("<em>words</em>", html)
        self.assertIn('alt="Photo"', html)
        self.assertIn(f'href="{PUBLICATION}/subscribe"', html)

    def test_rejects_traversal_or_foreign_post_urls(self):
        for slug in ("../escape", "%2e%2e%2fescape", "hello/../../escape", ""):
            with self.subTest(slug=slug), self.assertRaises(ValueError):
                blog.parse_feed(feed(slug=slug))
        with self.assertRaises(ValueError):
            blog.parse_feed(feed().replace(PUBLICATION.encode(), b"https://evil.test"))

    def test_rejects_malformed_feed_entities_and_invalid_date(self):
        for data in (b"<html>unavailable</html>", b"<rss>", feed(date="not a date"),
                     b'<!DOCTYPE x [<!ENTITY e SYSTEM "file:///etc/passwd">]><rss><channel>&e;</channel></rss>'):
            with self.subTest(data=data[:30]), self.assertRaises(ValueError):
                blog.parse_feed(data)

    def test_valid_empty_feed(self):
        self.assertEqual(blog.parse_feed(f"<rss><channel><link>{PUBLICATION}</link></channel></rss>".encode()), [])

    def test_description_fallback(self):
        data = feed().replace(b"<content:encoded><![CDATA[<p>Full article, not the summary.</p>]]></content:encoded>", b"")
        self.assertEqual(blog.parse_feed(data)[0]["html"], "Short summary.")

    def test_archive_retains_older_posts_and_updates_existing(self):
        old = blog.parse_feed(feed(slug="older"))
        current = blog.parse_feed(feed(title="Updated", date="Mon, 02 Sep 2024 12:00:00 GMT"))
        merged = blog.merge_posts(old + blog.parse_feed(feed()), current)
        self.assertEqual([p["slug"] for p in merged], ["hello", "older"])
        self.assertEqual(merged[0]["title"], "Updated")
        self.assertEqual(blog.merge_posts(merged, [], excluded=["older"]), current)

    def test_failed_import_preserves_archive_and_repeat_is_stable(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "posts.json"
            blog.sync_archive(path, feed())
            saved = path.read_bytes()
            blog.sync_archive(path, feed())
            self.assertEqual(saved, path.read_bytes())
            with self.assertRaises(ValueError):
                blog.sync_archive(path, b"not xml")
            self.assertEqual(saved, path.read_bytes())
            self.assertEqual(len(json.loads(saved)["posts"]), 1)


class BuildTests(unittest.TestCase):
    def test_builds_readable_article_index_and_metadata(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "site"
            blog.build_site(blog.parse_feed(feed(title='<script>x</script> & "Title"')), output)
            article = (output / "p/hello/index.html").read_text()
            index = (output / "index.html").read_text()
            self.assertIn('href="/p/hello/"', index)
            self.assertIn("Full article", article)
            self.assertIn("&lt;script&gt;x&lt;/script&gt;", article)
            self.assertNotIn("<script>", article)
            self.assertIn(f'href="{PUBLICATION}/p/hello"', article)
            self.assertIn('datetime="2024-08-30"', article)
            self.assertEqual((output / "CNAME").read_text().strip(), "blog.jibrilasif.com")
            self.assertTrue((output / "fonts/reckless-standard-m-regular.woff2").is_file())
            self.assertTrue((output / "404.html").is_file())

    def test_empty_state_and_defense_against_tampered_archive(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "site"
            blog.build_site([], output)
            self.assertIn("Nothing here yet", (output / "index.html").read_text())
            posts = blog.parse_feed(feed())
            posts[0]["html"] = '<script>bad()</script><p>Good</p>'
            blog.build_site(posts, output)
            self.assertNotIn("bad()", (output / "p/hello/index.html").read_text())
            posts[0]["slug"] = "../../outside"
            with self.assertRaises(ValueError):
                blog.build_site(posts, output)


if __name__ == "__main__":
    unittest.main()
