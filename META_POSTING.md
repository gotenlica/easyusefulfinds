# Instagram posting via Meta API

This repo includes a local helper script for official Instagram posting:

```bash
set -a
. ~/.hermes/secrets/meta.env
set +a
python3 tools/post_instagram.py --check
```

Post the current gaming finger sleeves draft:

```bash
set -a
. ~/.hermes/secrets/meta.env
set +a
python3 tools/post_instagram.py \
  --image-url https://gotenlica.github.io/easyusefulfinds/assets/gaming-finger-sleeves.jpg \
  --caption-file drafts/instagram-gaming-finger-sleeves.txt
```

## Fixing an expired token

Secrets live only on the server in:

`~/.hermes/secrets/meta.env`

Do not commit tokens or secrets to this repo.

Required variables for posting:

- `META_IG_USER_ID`
- `META_PAGE_ACCESS_TOKEN`
- `META_GRAPH_VERSION` (optional; defaults to `v20.0`)

Required variables for durable refresh:

- `META_APP_ID`
- `META_APP_SECRET`
- `META_SHORT_LIVED_TOKEN` (fresh User token generated from the same Meta app)

Refresh flow:

```bash
cd /home/goten/easyusefulfinds
python3 tools/refresh_meta_token.py
set -a
. ~/.hermes/secrets/meta.env
set +a
python3 tools/post_instagram.py --check
```

If `refresh_meta_token.py` says "App credential check failed", the saved App ID and App Secret do not match a valid Meta app. Fix those two values first in `~/.hermes/secrets/meta.env`.

If it says "Token exchange failed", generate a fresh User token in Meta Graph API Explorer from the same app with these permissions:

- `pages_show_list`
- `pages_read_engagement`
- `instagram_basic`
- `instagram_content_publish`

Then save it as `META_SHORT_LIVED_TOKEN` and rerun the refresh command.
