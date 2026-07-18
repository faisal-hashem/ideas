import json
import os
import subprocess
import sys
from pathlib import Path

from caption_generator import generate_caption
from drive_client import download_file, get_drive_service, list_photos
from instagram_client import create_media_container, publish_media, wait_until_ready

REPO_ROOT = Path(__file__).resolve().parent.parent
LOG_PATH = REPO_ROOT / "posted_log.json"
PHOTOS_DIR = REPO_ROOT / "public_photos"


def load_posted_ids():
    if not LOG_PATH.exists():
        return set()
    return set(json.loads(LOG_PATH.read_text())["posted_ids"])


def save_posted_ids(posted_ids):
    LOG_PATH.write_text(json.dumps({"posted_ids": sorted(posted_ids)}, indent=2) + "\n")


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


def main():
    posted_ids = load_posted_ids()

    drive_service = get_drive_service(os.environ["GOOGLE_SERVICE_ACCOUNT_JSON"])
    photos = list_photos(drive_service, os.environ["GOOGLE_DRIVE_FOLDER_ID"])
    unposted = [p for p in photos if p["id"] not in posted_ids]

    if not unposted:
        print("No new photos to post.")
        return

    photo = unposted[0]
    extension = photo["name"].rsplit(".", 1)[-1] if "." in photo["name"] else "jpg"
    filename = f"{photo['id']}.{extension}"

    print(f"Posting {photo['name']} ({photo['id']})")

    image_bytes = download_file(drive_service, photo["id"])
    photo_path = PHOTOS_DIR / filename
    photo_path.write_bytes(image_bytes)

    git_commit_and_push([photo_path], f"Add photo {photo['id']} for posting")
    image_url = raw_url_for(filename)

    caption = generate_caption(image_bytes, extension)
    print(f"Caption:\n{caption}")

    ig_account_id = os.environ["IG_ACCOUNT_ID"]
    access_token = os.environ["IG_ACCESS_TOKEN"]

    creation_id = create_media_container(ig_account_id, image_url, caption, access_token)
    wait_until_ready(creation_id, access_token)
    media_id = publish_media(ig_account_id, creation_id, access_token)
    print(f"Published Instagram media {media_id}")

    posted_ids.add(photo["id"])
    save_posted_ids(posted_ids)
    git_commit_and_push([LOG_PATH], f"Mark {photo['id']} as posted")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"Failed to post: {exc}", file=sys.stderr)
        raise
