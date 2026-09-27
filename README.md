# Jibril’s blog

A minimal, static home for public Substack posts at https://blog.jibrilasif.com.

Write and publish as usual at https://jibrilmoinuddin.substack.com. GitHub Actions
checks the public RSS feed hourly, archives the available article bodies, and
deploys GitHub Pages. The schedule can be delayed by GitHub. Run **Sync and publish
blog → Run workflow** for an immediate import. No Substack custom-domain fee,
embedded publication, client JavaScript, or third-party RSS proxy is needed.

## Local development

Requires Python 3.11 or newer.

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-dev.txt
.venv/bin/python -m coverage run --source=blog -m unittest discover -s tests -v
.venv/bin/python -m coverage report --fail-under=80
.venv/bin/python blog.py sync
.venv/bin/python blog.py build
.venv/bin/python -m http.server 4174 --directory _site --bind 127.0.0.1
```

Only public RSS content is imported. Substack may expose excerpts for paid posts;
the original-publication link lets readers continue there. Videos, forms, scripts,
and interactive embeds are removed; text, links, and images remain. HTML is
sanitized with nh3 and XML is parsed with defusedxml. Failed imports leave the
published site and last successful archive intact.

## Archives and removals

`data/posts.json` preserves posts after they leave Substack’s RSS window. Edits to
posts still in the feed are updated on the next sync. To remove an archived post,
add its slug to `excluded` in that file; it will disappear on deployment and stay
excluded from future imports. Older posts outside the feed window cannot be
discovered or updated by RSS alone. No private Substack API or credentials are used.

GitHub can disable scheduled workflows after 60 days without repository activity.
If that happens, re-enable the workflow under Actions or run it manually. New
imports are committed to the repository, keeping the archive independent of caches.

## Hosting

GitHub Pages uses the Actions deployment source and custom domain
`blog.jibrilasif.com`, with HTTPS enforced after certificate issuance. Namecheap
DNS has a `blog` CNAME pointing to `nodeDevcoder.github.io`. The separate repository
keeps the existing `jibrilasif.com` homepage deployment independent.

The Reckless Standard M webfont is Jibril’s licensed Displaay font, reused from his
personal site. It is not licensed for third-party redistribution or reuse.
