#!/usr/bin/env python3
"""Refresh Meta/Instagram Graph API tokens for Easy Useful Finds.

This uses the official Meta flow:
1. Exchange a fresh short-lived user token for a long-lived user token.
2. Fetch the connected Facebook Page token and Instagram business account ID.
3. Update ~/.hermes/secrets/meta.env without printing secrets.

Required in ~/.hermes/secrets/meta.env, environment, or CLI args:
  META_APP_ID
  META_APP_SECRET
  META_SHORT_LIVED_TOKEN   # fresh user token from Graph API Explorer

Optional:
  META_PAGE_ID             # selects the intended Facebook Page if multiple exist
  META_GRAPH_VERSION       # defaults to v20.0
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import shutil
import sys
from datetime import datetime, timezone
from getpass import getpass
from typing import Any
import urllib.error
import urllib.parse
import urllib.request

DEFAULT_ENV = Path.home() / ".hermes" / "secrets" / "meta.env"


def load_env(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.exists():
        return values
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def graph(version: str, method: str, path: str, params: dict[str, str]) -> dict[str, Any]:
    base = f"https://graph.facebook.com/{version}/{path.lstrip('/')}"
    if method == "GET":
        req = urllib.request.Request(base + "?" + urllib.parse.urlencode(params), method="GET")
    else:
        req = urllib.request.Request(base, data=urllib.parse.urlencode(params).encode(), method="POST")
    try:
        with urllib.request.urlopen(req, timeout=60) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        try:
            parsed = json.loads(body)
        except Exception:
            parsed = {"raw": body}
        raise RuntimeError(json.dumps(parsed, indent=2)) from exc


def update_env_file(path: Path, updates: dict[str, str]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    original = path.read_text(encoding="utf-8").splitlines() if path.exists() else []
    backup = path.with_suffix(path.suffix + ".bak." + datetime.now().strftime("%Y%m%d-%H%M%S"))
    if path.exists():
        shutil.copy2(path, backup)
    else:
        backup.write_text("", encoding="utf-8")

    seen: set[str] = set()
    out: list[str] = []
    for line in original:
        stripped = line.strip()
        if stripped and not stripped.startswith("#") and "=" in stripped:
            key = stripped.split("=", 1)[0].strip()
            if key in updates:
                out.append(f"{key}={updates[key]}")
                seen.add(key)
                continue
        out.append(line)

    if out and out[-1].strip():
        out.append("")
    for key, value in updates.items():
        if key not in seen:
            out.append(f"{key}={value}")

    path.write_text("\n".join(out).rstrip() + "\n", encoding="utf-8")
    os.chmod(path, 0o600)
    return backup


def require(name: str, args_value: str | None, env_values: dict[str, str], secret: bool = False) -> str:
    value = args_value or os.getenv(name) or env_values.get(name) or ""
    value = value.strip()
    if not value and secret and sys.stdin.isatty():
        value = getpass(f"{name}: ").strip()
    if not value:
        raise SystemExit(f"Missing {name}. Add it to {DEFAULT_ENV} or pass the matching CLI argument.")
    return value


def exp_to_text(value: Any) -> str:
    try:
        value = int(value)
    except Exception:
        return "unknown"
    if value == 0:
        return "never/unknown"
    return datetime.fromtimestamp(value, tz=timezone.utc).isoformat()


def main() -> int:
    parser = argparse.ArgumentParser(description="Exchange and save a long-lived Meta/Page token for Instagram posting.")
    parser.add_argument("--env-file", default=str(DEFAULT_ENV))
    parser.add_argument("--app-id")
    parser.add_argument("--app-secret")
    parser.add_argument("--short-lived-token")
    parser.add_argument("--page-id")
    parser.add_argument("--graph-version")
    parser.add_argument("--dry-run", action="store_true", help="Validate and print non-secret summary without writing meta.env.")
    args = parser.parse_args()

    env_path = Path(args.env_file).expanduser()
    env_values = load_env(env_path)
    version = args.graph_version or os.getenv("META_GRAPH_VERSION") or env_values.get("META_GRAPH_VERSION") or "v20.0"
    app_id = require("META_APP_ID", args.app_id, env_values)
    app_secret = require("META_APP_SECRET", args.app_secret, env_values, secret=True)
    short_token = require("META_SHORT_LIVED_TOKEN", args.short_lived_token, env_values, secret=True)
    desired_page_id = args.page_id or os.getenv("META_PAGE_ID") or env_values.get("META_PAGE_ID") or ""
    app_access_token = f"{app_id}|{app_secret}"

    print("Checking Meta app credentials...")
    try:
        app = graph(version, "GET", "app", {"access_token": app_access_token})
        print(f"OK app: {app.get('name', '<unnamed>')} ({app.get('id', app_id)})")
    except RuntimeError as exc:
        print("App credential check failed. META_APP_ID and META_APP_SECRET do not validate together.", file=sys.stderr)
        print(str(exc), file=sys.stderr)
        return 2

    print("Exchanging short-lived user token for long-lived user token...")
    try:
        exchanged = graph(
            version,
            "GET",
            "oauth/access_token",
            {
                "grant_type": "fb_exchange_token",
                "client_id": app_id,
                "client_secret": app_secret,
                "fb_exchange_token": short_token,
            },
        )
    except RuntimeError as exc:
        print("Token exchange failed. Generate a fresh User token from the same Meta app, then rerun.", file=sys.stderr)
        print(str(exc), file=sys.stderr)
        return 3

    long_user_token = exchanged.get("access_token")
    if not long_user_token:
        print("Meta did not return a long-lived access_token.", file=sys.stderr)
        return 4

    debug = graph(version, "GET", "debug_token", {"input_token": long_user_token, "access_token": app_access_token}).get("data", {})
    print(f"Long-lived user token valid: {debug.get('is_valid')} expires: {exp_to_text(debug.get('expires_at'))}")

    print("Finding connected Facebook Page and Instagram business account...")
    accounts = graph(
        version,
        "GET",
        "me/accounts",
        {
            "fields": "id,name,access_token,instagram_business_account{id,username}",
            "access_token": long_user_token,
        },
    ).get("data", [])

    candidates = [p for p in accounts if p.get("instagram_business_account") and p.get("access_token")]
    if desired_page_id:
        candidates = [p for p in candidates if str(p.get("id")) == str(desired_page_id)]
    if not candidates:
        print("No connected Page with an Instagram business account was found for this token.", file=sys.stderr)
        print("Make sure the User token includes pages_show_list, pages_read_engagement, instagram_basic, and instagram_content_publish.", file=sys.stderr)
        return 5

    page = candidates[0]
    ig = page["instagram_business_account"]
    page_token = page["access_token"]
    print(f"Selected Page: {page.get('name')} ({page.get('id')})")
    print(f"Selected Instagram: @{ig.get('username', '<unknown>')} ({ig.get('id')})")

    # Verify the Page token can see the IG account used by tools/post_instagram.py.
    account = graph(
        version,
        "GET",
        str(ig["id"]),
        {"fields": "id,username,account_type,media_count", "access_token": page_token},
    )
    print(f"Verified Instagram API access: @{account.get('username')} media_count={account.get('media_count')}")

    updates = {
        "META_GRAPH_VERSION": version,
        "META_APP_ID": app_id,
        "META_APP_SECRET": app_secret,
        "META_SHORT_LIVED_TOKEN": short_token,
        "META_LONG_LIVED_USER_TOKEN": long_user_token,
        "META_PAGE_ID": str(page["id"]),
        "META_IG_USER_ID": str(ig["id"]),
        "META_PAGE_ACCESS_TOKEN": page_token,
    }

    if args.dry_run:
        print("Dry run complete. meta.env was not changed.")
        return 0

    backup = update_env_file(env_path, updates)
    print(f"Updated {env_path}")
    print(f"Backup saved at {backup}")
    print("Now run: python3 tools/post_instagram.py --check")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
