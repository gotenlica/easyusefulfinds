#!/usr/bin/env python3
"""Post a single image to Instagram via the official Meta Graph API.

Reads credentials from environment variables, typically loaded from:
  ~/.hermes/secrets/meta.env

Required:
  META_IG_USER_ID
  META_PAGE_ACCESS_TOKEN

Optional:
  META_GRAPH_VERSION, defaults to v20.0

Examples:
  set -a; . ~/.hermes/secrets/meta.env; set +a
  python3 tools/post_instagram.py --check
  python3 tools/post_instagram.py \
    --image-url https://gotenlica.github.io/easyusefulfinds/assets/gaming-finger-sleeves.jpg \
    --caption-file drafts/instagram-gaming-finger-sleeves.txt
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request


def graph_base() -> str:
    version = os.getenv("META_GRAPH_VERSION", "v20.0").strip() or "v20.0"
    return f"https://graph.facebook.com/{version}"


def graph_get(path: str, params: dict[str, str]) -> dict:
    url = f"{graph_base()}/{path}?{urllib.parse.urlencode(params)}"
    with urllib.request.urlopen(url, timeout=60) as response:
        return json.loads(response.read().decode("utf-8"))


def graph_post(path: str, params: dict[str, str]) -> dict:
    data = urllib.parse.urlencode(params).encode("utf-8")
    request = urllib.request.Request(f"{graph_base()}/{path}", data=data, method="POST")
    with urllib.request.urlopen(request, timeout=120) as response:
        return json.loads(response.read().decode("utf-8"))


def require_env(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise SystemExit(f"Missing required environment variable: {name}")
    return value


def read_caption(args: argparse.Namespace) -> str:
    if args.caption_file:
        with open(args.caption_file, "r", encoding="utf-8") as handle:
            return handle.read().strip()
    if args.caption:
        return args.caption.strip()
    raise SystemExit("Provide --caption or --caption-file")


def main() -> int:
    parser = argparse.ArgumentParser(description="Publish an Instagram image post via Meta Graph API.")
    parser.add_argument("--check", action="store_true", help="Only verify the IG account/token.")
    parser.add_argument("--image-url", help="Public HTTPS image URL for the IG media container.")
    parser.add_argument("--caption", help="Caption text.")
    parser.add_argument("--caption-file", help="UTF-8 text file containing caption text.")
    parser.add_argument("--wait-seconds", type=int, default=8, help="Delay between create and publish calls.")
    args = parser.parse_args()

    ig_user_id = require_env("META_IG_USER_ID")
    access_token = require_env("META_PAGE_ACCESS_TOKEN")

    try:
        account = graph_get(
            ig_user_id,
            {
                "fields": "id,username,account_type,media_count",
                "access_token": access_token,
            },
        )
        print(json.dumps({"account": account}, indent=2))

        if args.check:
            return 0

        if not args.image_url:
            raise SystemExit("Provide --image-url or use --check")
        caption = read_caption(args)

        container = graph_post(
            f"{ig_user_id}/media",
            {
                "image_url": args.image_url,
                "caption": caption,
                "access_token": access_token,
            },
        )
        print(json.dumps({"container": container}, indent=2))

        time.sleep(max(args.wait_seconds, 0))

        published = graph_post(
            f"{ig_user_id}/media_publish",
            {
                "creation_id": container["id"],
                "access_token": access_token,
            },
        )
        print(json.dumps({"published": published}, indent=2))
        return 0
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        print(body, file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
