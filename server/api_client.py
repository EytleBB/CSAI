"""
5E Platform API client

All API calls go through gate.5eplay.com.
No authentication needed — UUID is a public identifier.
"""

import requests
import urllib3
import logging

urllib3.disable_warnings()

log = logging.getLogger("api_client")

GATE = "https://gate.5eplay.com"
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/130.0"}
TIMEOUT = 15


def _get(url):
    r = requests.get(url, timeout=TIMEOUT, verify=False, headers=HEADERS)
    r.raise_for_status()
    data = r.json()
    if data.get("code") != 0:
        raise RuntimeError(f"API error: {data.get('message')} (code={data.get('code')})")
    return data["data"]


# ── Match list ────────────────────────────────────────────────────────────────

def get_match_list(uuid, page=1, limit=20):
    url = (f"{GATE}/crane/http/api/data/match/list"
           f"?uuid={uuid}&page={page}&limit={limit}&match_type=-1&cs_type=0")
    return _get(url)


def get_mirage_matches(uuid, count=10):
    mirage = []
    for page in range(1, 6):
        matches = get_match_list(uuid, page=page, limit=20)
        if not matches:
            break
        for m in matches:
            if "mirage" in m.get("map", "").lower():
                mirage.append(m)
                if len(mirage) >= count:
                    return mirage
    return mirage


# ── Match detail ──────────────────────────────────────────────────────────────

def get_match_detail(match_id):
    url = f"{GATE}/crane/http/api/data/match/{match_id}"
    return _get(url)


def get_demo_url(match_id):
    detail = get_match_detail(match_id)
    return detail["main"]["demo_url"]


# ── Player lookup ─────────────────────────────────────────────────────────────

def extract_players(match_detail):
    players = []
    for group_key, group_num in [("group_1", 1), ("group_2", 2)]:
        for p in match_detail.get(group_key, []):
            ud = p.get("user_info", {}).get("user_data", {})
            steam = ud.get("steam", {})
            players.append({
                "uid": ud.get("uid"),
                "uuid": ud.get("uuid"),
                "steamid": steam.get("steamId", ""),
                "username": ud.get("username", ""),
                "domain": ud.get("domain", ""),
                "group": group_num,
            })
    return players


def get_current_match(uuid):
    """Get the user's current/active match details.

    Works during warmup/live match. Returns match detail or None.
    """
    for endpoint in ["current", "playing"]:
        try:
            url = f"{GATE}/crane/http/api/data/match/{endpoint}?uuid={uuid}"
            r = requests.get(url, timeout=TIMEOUT, verify=False, headers=HEADERS)
            r.raise_for_status()
            data = r.json()
            if data.get("code") == 0 and data.get("data"):
                log.info(f"match/{endpoint} returned data")
                return data["data"]
        except Exception as e:
            log.debug(f"match/{endpoint} failed: {e}")
    return None


def find_opponents_from_current_match(my_uuid):
    """Auto-detect opponents by querying 5E current match API.

    Returns dict of {steamid: {uuid, username, domain}} for opponents,
    or empty dict if not in a match.
    Polls up to 4 times with 15s delay.
    """
    import time

    for attempt in range(6):
        if attempt > 0:
            log.info(f"Polling for current match... attempt {attempt + 1}/6 (waiting 15s)")
            time.sleep(15)

        match_data = get_current_match(my_uuid)
        if not match_data:
            continue

        players = extract_players(match_data)
        if not players:
            continue

        # Find which group the user is in
        my_group = None
        for p in players:
            if p["uuid"] == my_uuid:
                my_group = p["group"]
                break

        if my_group is None:
            log.warning("Could not determine user's group in current match")
            continue

        # Opponents are in the other group
        opponent_group = 2 if my_group == 1 else 1
        found = {}
        for p in players:
            if p["group"] == opponent_group and p["steamid"]:
                found[str(p["steamid"])] = {
                    "uuid": p["uuid"],
                    "username": p["username"],
                    "domain": p["domain"],
                }
                log.info(f"Auto-detected opponent: {p['username']} ({p['steamid']})")

        if found:
            return found

    return {}


def _find_uuids_from_match_detail(match_detail, opponent_steamids):
    """Extract opponent UUIDs from a match detail response."""
    found = {}
    players = extract_players(match_detail)
    for p in players:
        sid = str(p["steamid"])
        if sid in opponent_steamids and sid not in found:
            found[sid] = {
                "uuid": p["uuid"],
                "username": p["username"],
                "domain": p["domain"],
            }
            log.info(f"Found opponent: {p['username']} ({sid})")
    return found


def find_opponent_uuids(my_uuid, opponent_steamids):
    """Find opponent UUIDs using multiple strategies:

    1. Try match/current and match/playing (works during live match)
    2. Poll match/current a few times with delay (match data may appear with delay)
    3. Fall back to searching recent match history
    """
    import time

    opponent_steamids = set(str(s) for s in opponent_steamids)
    found = {}

    # Strategy 1: Try current match endpoints (immediate + polling)
    log.info("Strategy 1: Trying match/current and match/playing...")
    for attempt in range(4):
        if attempt > 0:
            log.info(f"Polling attempt {attempt + 1}/4, waiting 15s...")
            time.sleep(15)

        match_data = get_current_match(my_uuid)
        if match_data:
            found = _find_uuids_from_match_detail(match_data, opponent_steamids)
            if found:
                log.info(f"Found {len(found)}/{len(opponent_steamids)} via current match")
                if len(found) == len(opponent_steamids):
                    return found
                break  # Got some results, move to fallback for the rest

    # Strategy 2: Direct steamid → UUID lookup
    remaining = opponent_steamids - set(found.keys())
    if remaining:
        log.info(f"Strategy 2: Trying direct steamid→UUID lookup for {len(remaining)} opponents...")
        for sid in list(remaining):
            info = steamid_to_uuid(sid)
            if info and info.get("uuid"):
                found[sid] = {
                    "uuid": info["uuid"],
                    "username": info.get("username", f"Player_{sid[-6:]}"),
                    "domain": info.get("domain", ""),
                }
                log.info(f"Direct lookup found: {found[sid]['username']} ({sid})")

    # Strategy 3: Check most recent matches (match may have just appeared in history)
    remaining = opponent_steamids - set(found.keys())
    if remaining:
        log.info(f"Strategy 3: Searching match history for {len(remaining)} remaining opponents...")
        for page in range(1, 4):
            matches = get_match_list(my_uuid, page=page, limit=20)
            if not matches:
                break
            for m in matches:
                detail = get_match_detail(m["match_id"])
                players = extract_players(detail)
                for p in players:
                    sid = str(p["steamid"])
                    if sid in remaining and sid not in found:
                        found[sid] = {
                            "uuid": p["uuid"],
                            "username": p["username"],
                            "domain": p["domain"],
                        }
                        log.info(f"Found opponent: {p['username']} ({sid})")
                if len(found) == len(opponent_steamids):
                    return found

    return found


# ── Steam ID → UUID direct lookup ─────────────────────────────────────────────

def _try_api(url, label):
    """Try an API URL, return (data, status_code) or (None, error)."""
    try:
        r = requests.get(url, timeout=TIMEOUT, verify=False, headers=HEADERS)
        data = r.json()
        return data, r.status_code
    except Exception as e:
        return None, str(e)


def probe_steamid_to_uuid(steamid):
    """Try multiple potential 5E API endpoints to convert steamid → uuid.

    Returns {uuid, username, domain} or None.
    """
    steamid = str(steamid)
    log.info(f"Probing 5E API for steamid {steamid}...")

    # List of potential endpoints to try
    endpoints = [
        f"{GATE}/crane/http/api/data/user/steam/{steamid}",
        f"{GATE}/crane/http/api/data/user/steamid/{steamid}",
        f"{GATE}/crane/http/api/data/user/profile?steamid={steamid}",
        f"{GATE}/crane/http/api/data/user/search?keyword={steamid}",
        f"{GATE}/crane/http/api/data/user/info?steamid={steamid}",
        f"{GATE}/crane/http/api/data/player/info?steamid={steamid}",
        f"{GATE}/crane/http/api/data/player/{steamid}",
        f"{GATE}/crane/http/api/data/steam/bindinfo?steamid={steamid}",
        f"{GATE}/crane/http/api/data/user/steam?steamId={steamid}",
        f"{GATE}/crane/http/api/data/user/by-steam/{steamid}",
        f"{GATE}/crane/http/api/v1/user/steam/{steamid}",
        f"{GATE}/crane/http/api/v1/user/search?keyword={steamid}",
    ]

    results = []
    for url in endpoints:
        data, status = _try_api(url, url)
        short_url = url.replace(GATE, "")
        result = {"url": short_url, "status": status}

        if data and isinstance(data, dict):
            code = data.get("code")
            result["code"] = code
            result["message"] = data.get("message", "")

            if code == 0 and data.get("data"):
                result["has_data"] = True
                result["data_preview"] = str(data["data"])[:500]
                log.info(f"  HIT: {short_url} → code=0, has data!")

                # Try to extract UUID from response
                d = data["data"]
                uuid = None
                if isinstance(d, dict):
                    uuid = d.get("uuid") or d.get("user_uuid")
                    if not uuid and "user_data" in d:
                        uuid = d["user_data"].get("uuid")
                elif isinstance(d, list) and len(d) > 0:
                    uuid = d[0].get("uuid") or d[0].get("user_uuid")

                if uuid:
                    result["uuid_found"] = uuid
                    log.info(f"  UUID FOUND: {uuid}")
            else:
                result["has_data"] = False
                log.debug(f"  MISS: {short_url} → code={code}")
        else:
            result["has_data"] = False

        results.append(result)

    return results


def steamid_to_uuid(steamid):
    """Convert a Steam ID to 5E UUID using probed API endpoints.

    Returns {uuid, username, domain} or None.
    """
    probe_results = probe_steamid_to_uuid(steamid)
    for r in probe_results:
        if r.get("uuid_found"):
            return {"uuid": r["uuid_found"]}
        if r.get("has_data") and r.get("data_preview"):
            # Try to parse the data more carefully
            data, _ = _try_api(GATE + r["url"], "retry")
            if data and data.get("code") == 0 and data.get("data"):
                d = data["data"]
                if isinstance(d, dict):
                    uuid = d.get("uuid") or d.get("user_uuid") or d.get("uid")
                    username = d.get("username") or d.get("nickname") or d.get("name", "")
                    domain = d.get("domain", "")
                    if uuid:
                        return {"uuid": uuid, "username": username, "domain": domain}
    return None


# ── Arena player search (new flow: username → domain → demos) ─────────────────

ARENA = "https://arena.5eplay.com"


def search_player(username):
    """Search 5E arena by username. Returns (domain, matched_username) or (None, None)."""
    url = f"{ARENA}/api/search?keywords={requests.utils.quote(username)}"
    try:
        r = requests.get(url, timeout=TIMEOUT, verify=False, headers=HEADERS)
        r.raise_for_status()
        d = r.json()
        users = d.get("data", {}).get("user", {}).get("list", [])
        if not users:
            log.warning(f"search_player: no results for '{username}'")
            return None, None
        return users[0]["domain"], users[0]["username"]
    except Exception as e:
        log.warning(f"search_player({username}) failed: {e}")
        return None, None


def get_mirage_demos_by_domain(domain, count=10):
    """Paginate through a player's match history and collect up to `count` Mirage demos.

    Tries match_type=9 (ranked, always has demo_url) first, then falls through to
    other match_types if still short of `count`.  All match_types share one
    seen_codes set so duplicates are never returned twice.

    Returns list of {match_code, demo_url}.
    """
    results = []
    seen_codes = set()

    for candidate in ["?match_type=9", "", "?match_type=1", "?match_type=8"]:
        if len(results) >= count:
            break

        sep = "&" if "?" in candidate else "?"
        found_any = False  # did this match_type return any new data at all?

        for page in range(1, 30):
            if len(results) >= count:
                break
            try:
                url = f"{ARENA}/api/data/player/{domain}{candidate}{sep}page={page}"
                r = requests.get(url, timeout=TIMEOUT, verify=False, headers=HEADERS)
                r.raise_for_status()
                matches = r.json().get("match", [])
                if not matches:
                    break

                new_on_page = False
                for m in matches:
                    mc = m.get("match_code", "")
                    if not mc or mc in seen_codes:
                        continue
                    seen_codes.add(mc)
                    new_on_page = True
                    found_any = True
                    if m.get("map") == "de_mirage" and m.get("demo_url"):
                        results.append({"match_code": mc, "demo_url": m["demo_url"]})
                        if len(results) >= count:
                            break

                if not new_on_page:   # whole page was duplicates → this type exhausted
                    break

            except Exception as e:
                log.warning(f"get_mirage_demos {candidate} page {page} failed: {e}")
                break

        if not found_any:
            log.debug(f"get_mirage_demos: match_type {candidate!r} returned no data for {domain}")

    if not results:
        log.warning(f"get_mirage_demos: no Mirage demos found for domain {domain}")
    return results


def get_steamid_for_player(match_code, username):
    """Extract a player's steamid from a match detail by matching username."""
    try:
        detail = get_match_detail(match_code)
        for p in extract_players(detail):
            if p.get("username") == username:
                return str(p["steamid"])
    except Exception as e:
        log.warning(f"get_steamid_for_player({match_code}) failed: {e}")
    return None


# ── Demo download ─────────────────────────────────────────────────────────────

def download_demo(url, save_path, progress_cb=None):
    r = requests.get(url, stream=True, timeout=120, verify=False, headers=HEADERS)
    r.raise_for_status()
    total = int(r.headers.get("content-length", 0))
    downloaded = 0

    with open(save_path, "wb") as f:
        for chunk in r.iter_content(chunk_size=65536):
            f.write(chunk)
            downloaded += len(chunk)
            if progress_cb:
                progress_cb(downloaded, total)

    return save_path
