#!/usr/bin/env python3
"""Quick test: parse `home.ha.html` using `parse_router_page` from `parser.py`.
This script avoids touching the DB and only exercises the HTML parsing logic.
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
html_file = ROOT / 'home.ha.html'

if not html_file.exists():
    print(f"Sample HTML not found at {html_file}")
    raise SystemExit(1)

with open(html_file, 'r', encoding='utf-8', errors='ignore') as f:
    html = f.read()

# Import parse_router_page from parser
import sys
# Ensure repo root is on sys.path so we can import modules from the project root when
# this script is executed from the repo/tests directory.
sys.path.insert(0, str(ROOT))
from parser import parse_router_page

devices = parse_router_page(html)
print(f"Found {len(devices)} devices")
if devices:
    print(json.dumps(devices[:5], indent=2))
