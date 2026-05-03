"""Pinterest auto-publication — STUB / placeholder.

Not implemented yet. Provisioned skeleton so a future sprint can fill it.

Architecture cible
==================
1. **OAuth Pinterest Developer App** (`PINTEREST_APP_ID`, `PINTEREST_APP_SECRET`)
   - Exchange one-time `code` from `oauth/start` redirect for `access_token`
     + `refresh_token` (long-lived). Persist in `platform_settings.pinterest`
     and per-site if multi-tenant.
   - Required scopes : `pins:write`, `boards:read`, `user_accounts:read`.

2. **Board provisioning per site**
   - On site go-live, create one Pinterest board named after `brand.name`,
     description from `site.about_rich.tagline`.
   - Persist `board_id` in `site.pinterest.board_id`.

3. **Auto-pin worker (cron)**
   - Every 4 hours, pick up to 6 products from `db.products` for sites with
     `pinterest.auto_pin=True` and pin :
       - `media_source` = product main image (HD)
       - `link` = `https://{custom_domain}/products/{slug}?utm_source=pinterest`
       - `title` = product.name + brand suffix
       - `description` = AEO snippet (already 40-60 words, perfect for Pinterest)
         + 5 hashtags from `site.niche` + `niche.keyword_universe`
   - Throttle so we don't hit Pinterest's 100 pins/day limit per account.

4. **Performance tracking**
   - Daily `analytics/pin_performance` poll per board, store in
     `pinterest_metrics`. Surface in `Site Analytics > Social` tab.

5. **De-provisioning**
   - If site goes back to `draft` or `archived`, delete or hide the board.

TODO
====
- [ ] Add `routes/pinterest.py` with OAuth start/callback (admin only).
- [ ] Create `db.platform_settings.pinterest` schema doc.
- [ ] Implement `create_board(site, access_token)`.
- [ ] Implement `pin_product(product, site, access_token)` using REST API
      `POST /v5/pins`.
- [ ] Schedule `pinterest_auto_pin_tick` every 4h in APScheduler.
- [ ] Add Step 10 QA check : `pinterest_connected` (warn if niche has
      `pinterest_potential=True` and not connected).
- [ ] Add toggle in `SiteSettings.jsx` -> Section Social.

.env required
=============
    PINTEREST_APP_ID=
    PINTEREST_APP_SECRET=
    PINTEREST_OAUTH_REDIRECT_URI=https://altiaro.com/admin/integrations/pinterest/callback
    # Optional fixed token for single-tenant test runs :
    PINTEREST_ACCESS_TOKEN=

Until this module is implemented, every public function below returns
`{"ok": False, "reason": "not_implemented"}` to keep callers safe.
"""
from __future__ import annotations

from typing import Any, Dict, Optional


async def is_configured() -> bool:
    """Returns True when the Pinterest credentials are present in env."""
    import os
    return bool(os.environ.get("PINTEREST_APP_ID") and os.environ.get("PINTEREST_APP_SECRET"))


async def create_board_for_site(site_id: str) -> Dict[str, Any]:
    return {"ok": False, "reason": "not_implemented", "see": "services/pinterest_publisher.py"}


async def pin_product(site_id: str, product_id: str) -> Dict[str, Any]:
    return {"ok": False, "reason": "not_implemented", "see": "services/pinterest_publisher.py"}


async def auto_pin_tick() -> Dict[str, Any]:
    """Cron entrypoint — currently a no-op. Schedule once OAuth is wired."""
    return {"ok": False, "reason": "not_implemented"}
