# Jibril’s blog

A minimal, static home for public Substack posts at https://blog.jibrilasif.com.

Write and publish as usual at https://jibrilmoinuddin.substack.com. The RSS importer
archives the available public article bodies. GitHub Actions deploys that archive
to GitHub Pages on every push to main. No Substack custom-domain fee,
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

Substack currently returns HTTP 403 to this repository’s GitHub-hosted runners.
RSS import therefore runs locally; publishing the saved archive is independent
of Substack availability. Run `blog.py sync`, commit `data/posts.json`, and push
to main to publish an import. Imports are committed, keeping the archive
independent of caches. Running the Pages workflow manually redeploys the saved
archive; it does not fetch new posts.

## Hosting

GitHub Pages uses the Actions deployment source and custom domain
`blog.jibrilasif.com`, with HTTPS enforced after certificate issuance. Namecheap
DNS has a `blog` CNAME pointing to `nodeDevcoder.github.io`. The separate repository
keeps the existing `jibrilasif.com` homepage deployment independent.

The Reckless Standard M webfont is Jibril’s licensed Displaay font, reused from his
personal site. It is not licensed for third-party redistribution or reuse.
