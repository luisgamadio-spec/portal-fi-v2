#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
RH-5B.2 -- dedicated local Human UAT server. Two guarantees the plain
`python -m http.server` (used by every automated test in this repo)
does NOT provide:

  1. Rooted EXACTLY at this worktree (the directory this script lives
     in, one level up from tests/) -- never a parent directory shared
     by multiple Portal V2 worktrees, eliminating any path ambiguity.
  2. Every response carries `Cache-Control: no-store, no-cache,
     must-revalidate` + `Pragma: no-cache` -- plain http.server sends
     only `Last-Modified`, no Cache-Control at all, so a browser that
     already cached an asset from an EARLIER visit to the same URL
     (e.g. a prior Wave's UAT session) can silently keep serving that
     stale copy on a normal reload. This was the proven root cause of
     the "não mudou nada" Human report this Wave.

Usage: python tests/_rh5b2_no_cache_server.py [port]  (default 8082)
"""
import http.server
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class NoCacheHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=ROOT, **kwargs)

    def end_headers(self):
        self.send_header('Cache-Control', 'no-store, no-cache, must-revalidate')
        self.send_header('Pragma', 'no-cache')
        super().end_headers()


def main():
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8082
    server = http.server.ThreadingHTTPServer(('127.0.0.1', port), NoCacheHandler)
    print('RH-5B.2 dedicated no-cache server')
    print('root:', ROOT)
    print('url: http://127.0.0.1:%d/' % port)
    server.serve_forever()


if __name__ == '__main__':
    main()
