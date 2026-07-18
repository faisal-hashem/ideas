import json
import os
import random
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from caption_generator import categorize_photo, generate_caption
from drive_client import download_file, get_drive_service, list_photos
from image_processing import fit_to_instagram_ratio
from instagram_client import (
    create_carousel_container,
    create_carousel_item,
    create_media_container,
    publish_media,
    wait_until_ready,
)

REPO_ROOT = Path(__file__).resolve().parent.parent
PHOTOS_DIR = REPO_ROOT / "public_photos"
HISTORY_PATH = REPO_ROOT / "post_history.json"
META_PATH = REPO_ROOT / "photo_meta.json"

COOLDOWN_POSTS = 10        # a photo can't repeat until this many posts have gone out
MIN_CAROUSEL_GROUP = 3     # need at least this many same-theme photos to offer a slideshow
MAX_CAROUSEL_SIZE = 4
CAROUSEL_PROBABILITY = 0.4


def load_json(path, default):
    if not path.exists():
        return default
    return json.loads(path.read_text())


def save_json(path, data):
    path.write_text(json.dumps(data, indent=2) + "\n")


def git_commit_and_push(paths, message):
    subprocess.run(["git", "add", *[str(p) for p in paths]], check=True, cwd=REPO_ROOT)
    result = subprocess.run(["git", "diff", "--cached", "--quiet"], cwd=REPO_ROOT)
    if result.returncode == 0:
        return
    subprocess.run(["git", "commit", "-m", message], check=True, cwd=REPO_ROOT)
    subprocess.run(["git", "push"], check=True, cwd=REPO_ROOT)


def raw_url_for(filename):
    repo = os.environ["GITHUB_REPOSITORY"]
    branch = os.environ.get("GITHUB_REF_NAME", "main")
    return f"https://raw.githubusercontent.com/{repo}/{branch}/public_photos/{filename}"


def recently_used_ids(history):
    used = set()
    for entry in history[-COOLDOWN_POSTS:]:
        used.update(entry["file_ids"])
    return used


def last_used_at(history, file_id):
    for entry in reversed(history):
        if file_id in entry["file_ids"]:
            return entry["posted_at"]
    return ""


def ensure_metadata(photos, meta, drive_service):
    changed = False
    for photo in photos:
        if photo["id"] in meta:
            continue
        processed = fit_to_instagram_ratio(download_file(drive_service, photo["id"]))
        info = categorize_photo(processed)
        meta[photo["id"]] = info
        changed = True
        print(f"Categorized {photo['name']}: {info}")
    return changed


def pick_carousel_group(eligible, meta):
    tiers = [
        lambda p: (meta[p["id"]]["category"], meta[p["id"]].get("location"), meta[p["id"]].get("has_person")),
        lambda p: (meta[p["id"]]["category"], meta[p["id"]].get("location")),
        lambda p: (meta[p["id"]]["category"],),
    ]
    for key_fn in tiers:
        groups = {}
        for photo in eligible:
            groups.setdefault(key_fn(photo), []).append(photo)
        qualifying = [g for g in groups.values() if len(g) >= MIN_CAROUSEL_GROUP]
        if qualifying:
            return max(qualifying, key=len)
    return None


def order_by_freshness(photos, history):
    return sorted(photos, key=lambda photo: (last_used_at(history, photo["id"]), random.random()))


def choose_photos(eligible, meta, history):
    group = pick_carousel_group(eligible, meta)
    if group and random.random() < CAROUSEL_PROBABILITY:
        return order_by_freshness(group, history)[:MAX_CAROUSEL_SIZE], "carousel"
    return order_by_freshness(eligible, history)[:1], "single"


def main():
    history = load_json(HISTORY_PATH, [])
    meta = load_json(META_PATH, {})

    drive_service = get_drive_service(os.environ["GOOGLE_SERVICE_ACCOUNT_JSON"])
    photos = list_photos(drive_service, os.environ["GOOGLE_DRIVE_FOLDER_ID"])
    if not photos:
        print("No photos in Drive folder.")
        return

    used = recently_used_ids(history)
    eligible = [p for p in photos if p["id"] not in used]
    if not eligible:
        print("Every photo is on cooldown (library smaller than the cooldown window) — reusing full library.")
        eligible = photos

    if ensure_metadata(eligible, meta, drive_service):
        save_json(META_PATH, meta)
        git_commit_and_push([META_PATH], "Update photo metadata")

    chosen, post_type = choose_photos(eligible, meta, history)
    print(f"Selected {post_type} post with {len(chosen)} photo(s): {[p['name'] for p in chosen]}")

    saved = []
    processed_images = []
    for photo in chosen:
        processed = fit_to_instagram_ratio(download_file(drive_service, photo["id"]))
        filename = f"{photo['id']}.jpg"
        (PHOTOS_DIR / filename).write_bytes(processed)
        processed_images.append(processed)
        saved.append((photo, filename))

    git_commit_and_push(
        [PHOTOS_DIR / filename for _, filename in saved],
        f"Add photo(s) for posting: {', '.join(photo['name'] for photo, _ in saved)}",
    )

    caption = generate_caption(processed_images)
    print(f"Caption:\n{caption}")

    ig_account_id = os.environ["IG_ACCOUNT_ID"]
    access_token = os.environ["IG_ACCESS_TOKEN"]

    if post_type == "carousel":
        children = []
        for _, filename in saved:
            item_id = create_carousel_item(ig_account_id, raw_url_for(filename), access_token)
            wait_until_ready(item_id, access_token)
            children.append(item_id)
        creation_id = create_carousel_container(ig_account_id, children, caption, access_token)
    else:
        creation_id = create_media_container(ig_account_id, raw_url_for(saved[0][1]), caption, access_token)

    wait_until_ready(creation_id, access_token)
    media_id = publish_media(ig_account_id, creation_id, access_token)
    print(f"Published Instagram media {media_id}")

    history.append({
        "file_ids": [photo["id"] for photo, _ in saved],
        "type": post_type,
        "posted_at": datetime.now(timezone.utc).isoformat(),
    })
    save_json(HISTORY_PATH, history)
    git_commit_and_push([HISTORY_PATH], f"Record {post_type} post in history")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"Failed to post: {exc}", file=sys.stderr)
        raise
