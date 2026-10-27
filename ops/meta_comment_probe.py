"""Read-only probe: why can't the Page comment on its Reels? Posts nothing."""
import os
import requests
import meta_publish as mp

def show(what, r):
    try:
        b = r.json()
    except ValueError:
        b = r.text[:200]
    err = b.get("error") if isinstance(b, dict) else None
    msg = f"{what}: HTTP {r.status_code} " + (f"ERROR {err.get('code')}/{err.get('error_subcode')} {err.get('message')}" if err else str(b)[:300])
    print(f"::notice::{msg}")

tok = os.environ["META_TOKEN"]
show("token permissions", requests.get(f"{mp.GRAPH}/me/permissions", params={"access_token": tok}, timeout=60))
page_token, ig = mp.page_credentials()
print(f"::notice::ig account linked: {bool(ig)}")
show("page token scopes", requests.get(f"{mp.GRAPH}/debug_token", params={"input_token": page_token, "access_token": tok}, timeout=60))
for name, oid in [("FB reel 26 Oct", "1167319915959426"), ("IG reel 26 Oct", "18432419437144806"),
                  ("FB photo 25 Oct", "1297351930130917_122115284565489082")]:
    show(f"{name} read", requests.get(f"{mp.GRAPH}/{oid}", params={"fields": "id", "access_token": page_token}, timeout=60))
    show(f"{name} comments read", requests.get(f"{mp.GRAPH}/{oid}/comments", params={"limit": 3, "access_token": page_token}, timeout=60))
