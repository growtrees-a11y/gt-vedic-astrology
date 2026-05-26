#!/usr/bin/env bash
set -euo pipefail

# ── Set ephemeris path so pyswisseph finds the data files ──────────
export SWEPH_PATH="${SWEPH_PATH:-/usr/share/sweph/ephe}"

# Attempt to switch to real Swiss Ephemeris if pyswisseph is available
python3 -c "
import sys
try:
    import swe
    swe.set_ephe_path('${SWEPH_PATH}')
    print('[ephe] pyswisseph loaded, ephe path set to', '${SWEPH_PATH}')
except ImportError:
    print('[ephe] pyswisseph not installed — using mock_swe')
except Exception as exc:
    print('[ephe] pyswisseph import error:', exc, '— falling back to mock_swe')
" 2>&1 || true

echo "[start] Launching ${*:-uvicorn app:app --host 0.0.0.0 --port 8000}"
exec "$@"
