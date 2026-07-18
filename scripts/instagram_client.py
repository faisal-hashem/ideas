import time

import requests

GRAPH_API_BASE = "https://graph.instagram.com/v21.0"


def create_media_container(ig_account_id, image_url, caption, access_token):
    response = requests.post(
        f"{GRAPH_API_BASE}/{ig_account_id}/media",
        data={"image_url": image_url, "caption": caption, "access_token": access_token},
        timeout=30,
    )
    response.raise_for_status()
    return response.json()["id"]


def wait_until_ready(creation_id, access_token, timeout_seconds=120, poll_seconds=5):
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        response = requests.get(
            f"{GRAPH_API_BASE}/{creation_id}",
            params={"fields": "status_code", "access_token": access_token},
            timeout=30,
        )
        response.raise_for_status()
        status = response.json().get("status_code")
        if status == "FINISHED":
            return
        if status == "ERROR":
            raise RuntimeError(f"Instagram failed to process media container {creation_id}")
        time.sleep(poll_seconds)
    raise TimeoutError(f"Media container {creation_id} did not finish processing in time")


def publish_media(ig_account_id, creation_id, access_token):
    response = requests.post(
        f"{GRAPH_API_BASE}/{ig_account_id}/media_publish",
        data={"creation_id": creation_id, "access_token": access_token},
        timeout=30,
    )
    response.raise_for_status()
    return response.json()["id"]
