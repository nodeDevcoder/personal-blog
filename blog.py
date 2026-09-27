"""Import public Substack posts and build a static blog."""


def parse_feed(data):
    raise NotImplementedError


def merge_posts(existing, incoming, excluded=()):
    raise NotImplementedError


def build_site(posts, output):
    raise NotImplementedError


def sync_archive(path, data):
    raise NotImplementedError
