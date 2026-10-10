#!/usr/bin/env python3
"""CI check: every src= or href= in index.html resolves to a file in the tree.

Relative URLs are resolved against tar1090/rootfs/var/www/tar1090/, the same
way Flask's static serving does. Absolute and off-site URLs (https://, //)
are skipped. Exits 1 with a ::error:: annotation on the first failure batch.
"""

import os
import re
import sys

HTML_SOURCE = os.path.join('tar1090', 'rootfs', 'var', 'www', 'tar1090')
REF_RE = re.compile(r'(?:src|href)\s*=\s*["\']([^"\']+)["\']')


def resolve(ref):
    """Absolute in-tree path for a relative URL, or a skip marker."""
    ref = ref.split('#', 1)[0].split('?', 1)[0]
    if not ref or ref.startswith(('https://', 'http://', '//', 'data:', 'blob:', 'mailto:')):
        return None
    return os.path.join(HTML_SOURCE, *ref.split('/'))


def main():
    html_path = os.path.join(HTML_SOURCE, 'index.html')
    with open(html_path, 'r', encoding='utf-8') as f:
        html = f.read()

    missing = []
    seen = set()
    for ref in REF_RE.findall(html):
        path = resolve(ref)
        if path is None or path in seen:
            continue
        seen.add(path)
        if not os.path.isfile(path):
            missing.append((ref, path))

    if missing:
        for ref, path in missing:
            print(f"::error::index.html references {ref!r} -> {path}, which is not in the tree")
        return 1
    print(f"OK: {len(seen)} referenced file(s) resolve in-tree")
    return 0


if __name__ == '__main__':
    sys.exit(main())