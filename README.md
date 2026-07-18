# Instagram Auto-Poster

Posts one photo from a Google Drive folder to Instagram, 3x/day, with an
AI-generated caption and hashtags. Runs entirely on GitHub Actions — nothing
needs to stay on locally.

**Privacy note:** this repo must be **public**. Each photo gets committed to
`public_photos/` and served via `raw.githubusercontent.com` so Instagram's
API can fetch it — photos remain in git history even after being posted.
Don't use this for anything you don't want permanently public.

## How it works

1. You drop new photos into a Google Drive folder (see the iPhone Shortcuts
   step below to automate this from an iCloud album).
2. 3x/day, a GitHub Actions workflow runs `scripts/post_to_instagram.py`,
   which:
   - Lists photos in the Drive folder, skips any already posted
     (tracked in `posted_log.json`).
   - Downloads the oldest unposted photo and commits it to `public_photos/`.
   - Sends the photo to Claude to generate a caption + hashtags.
   - Publishes it to Instagram via the Graph API using the raw GitHub URL.
   - Marks it posted in `posted_log.json`.

## One-time setup

### 1. Google Drive access

1. Create a Google Cloud project → enable the **Google Drive API**.
2. Create a **service account**, generate a JSON key for it.
3. Create (or pick) a Drive folder for photos, share it with the service
   account's email address (Viewer access).
4. Copy the folder ID from its URL (`https://drive.google.com/drive/folders/<FOLDER_ID>`).

### 2. Instagram / Meta access

Uses the **Instagram API with Instagram Login** (no Facebook Page needed —
just a Business or Creator Instagram account, which this account already is).

1. Create an app at [developers.facebook.com](https://developers.facebook.com)
   and add the **Instagram** product (Instagram API setup with Instagram Login).
2. Add your Instagram account as a tester/authorized user and complete
   "Business Login for Instagram" to generate a short-lived access token,
   then exchange it for a **long-lived token** (`grant_type=ig_exchange_token`).
3. Get your **Instagram User ID** via `GET https://graph.instagram.com/me?fields=id,username`.

⚠️ Long-lived tokens expire after ~60 days. You'll need to manually refresh
`IG_ACCESS_TOKEN` in GitHub Secrets periodically, or the workflow will start
failing.

### 3. Anthropic API key

Get one at [console.anthropic.com](https://console.anthropic.com).

### 4. GitHub repo secrets

In this repo's Settings → Secrets and variables → Actions, add:

| Secret | Value |
|---|---|
| `GOOGLE_SERVICE_ACCOUNT_JSON` | full contents of the service account JSON key file |
| `GOOGLE_DRIVE_FOLDER_ID` | the Drive folder ID from step 1 |
| `ANTHROPIC_API_KEY` | your Anthropic API key |
| `IG_ACCESS_TOKEN` | long-lived Instagram access token |
| `IG_ACCOUNT_ID` | Instagram Business Account ID |

Also make sure this repo is **public** (Settings → General → Danger Zone).

### 5. iPhone → Google Drive automation

In the Shortcuts app on your iPhone:

1. Go to **Automation** → **+** → **New Personal Automation** → **Photos**.
2. Trigger: "Photo Added" to a specific Album.
3. Action: **Save File** → choose your Google Drive folder.
4. Turn off "Ask Before Running" so it's fully automatic.

Now any photo added to that album syncs to Drive, and the bot will pick it
up on its next scheduled run.

## Testing

Trigger a run manually anytime from the **Actions** tab → "Post to
Instagram" → **Run workflow**, instead of waiting for the schedule.

## Schedule

Defined in `.github/workflows/post-to-instagram.yml` as UTC cron times
(currently ~9am / 2pm / 7pm US Eastern). Adjust the `cron` lines to change
frequency or timing.

## Local testing

```
pip install -r requirements.txt
export GOOGLE_SERVICE_ACCOUNT_JSON='...'
export GOOGLE_DRIVE_FOLDER_ID='...'
export ANTHROPIC_API_KEY='...'
export IG_ACCESS_TOKEN='...'
export IG_ACCOUNT_ID='...'
export GITHUB_REPOSITORY='faisal-hashem/ideas'
export GITHUB_REF_NAME='main'
python scripts/post_to_instagram.py
```
