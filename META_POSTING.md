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

## Current known blocker

The saved `META_PAGE_ACCESS_TOKEN` expired. Refresh it in Meta Graph API Explorer or the app dashboard, then update:

`~/.hermes/secrets/meta.env`

Required variables:

- `META_IG_USER_ID`
- `META_PAGE_ACCESS_TOKEN`
- `META_GRAPH_VERSION` (optional; defaults to `v20.0`)

Do not commit tokens or secrets to this repo.
