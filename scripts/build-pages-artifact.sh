#!/usr/bin/env bash
# GL-1E (Go-Live deployment reconciliation) -- single source of truth for
# Portal V2's production artifact allowlist. Called identically by
# .github/workflows/pages.yml (real future deploy) and by a local
# production-like smoke test (GL-1F) -- so "what actually gets deployed"
# and "what was smoke-tested locally" can never silently drift apart.
#
# Modeled directly on the Secure repo's own proven pattern
# (.github/workflows/pages.yml): a POSITIVE allowlist, never a blanket
# copy of the working tree. Anything not explicitly listed here is
# excluded by construction -- tests/*.py, test harness HTML, diagnostic
# bridges, screenshots, docs/, README.md, .git, .gitignore, local runtime
# config, Supabase migration source (there is none in this repo), and any
# secret are all excluded simply by never being copied.
#
# Usage: build-pages-artifact.sh <output-dir>
set -euo pipefail

OUT="${1:?Usage: build-pages-artifact.sh <output-dir>}"
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$HERE"

rm -rf "$OUT"
mkdir -p "$OUT"

# --- Required runtime entry point ---
cp index.html "$OUT/index.html"
touch "$OUT/.nojekyll"

# --- Static assets (recursive) -- includes the GL-1B vendored design-
# system assets under assets/css/vendor/ and assets/js/vendor/.
#
# EXCLUDES *.local.js explicitly (Gate 16/31/32): a real `git checkout`
# in CI never materializes these gitignored, never-committed files, so
# the real GitHub Actions run is safe by construction either way -- but
# THIS script is also used for local smoke-testing directly against a
# developer's own working tree, which MAY have a real
# intelligence-runtime-config.local.js sitting on disk (never committed,
# but physically present). Relying on "CI wouldn't have it" is not
# enough for a script whose whole point is local/CI parity -- so this
# copy step excludes the pattern explicitly, defense in depth, rather
# than assuming. ---
if [ -d assets ]; then
  mkdir -p "$OUT/assets"
  ( cd assets && find . -type f ! -name '*.local.js' -print0 ) | \
    while IFS= read -r -d '' f; do
      mkdir -p "$OUT/assets/$(dirname "$f")"
      cp "assets/$f" "$OUT/assets/$f"
    done
fi

# --- Runtime-required config JSON only (Gate 22) -- NOT the whole
# config/ directory. The 3 Python governance scripts and
# production-fingerprint.json stay excluded; they are dev/CI tooling,
# never fetched by the browser app. ---
mkdir -p "$OUT/config"
cp config/module-registry.json "$OUT/config/module-registry.json"
cp config/landing-groups.json "$OUT/config/landing-groups.json"

# --- Narrowly-scoped fixture data (Gate 20/21) -- ONLY the top-level
# *.json files under tests/fixtures/, never the harness .html/.js files
# that live alongside them, never the rest of tests/. This is required
# ONLY because the committed default config still has real transport
# unconfigured (supabaseUrl: null) as of this wave -- once a real
# production config is wired into index.html (a later, explicitly
# separate gate), every module using isRealTransport() switches to real
# transport automatically and this fixture data stops being needed. It
# remains here, narrowly, so that deploying EXACTLY what is committed
# today works correctly without a broken fixture fetch. ---
if [ -d tests/fixtures ]; then
  mkdir -p "$OUT/tests/fixtures"
  find tests/fixtures -maxdepth 1 -type f -name '*.json' -exec cp {} "$OUT/tests/fixtures/" \;
fi

echo "Artifact assembled at: $OUT"
echo "Contents:"
find "$OUT" -type f | sort
