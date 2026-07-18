# Instagram Auto-Poster

Posts to Instagram from a Google Drive folder, 3x/day, with an AI-generated
caption and hashtags. Runs entirely on GitHub Actions — nothing needs to stay
on locally.

**Privacy note:** this repo must be **public**. Each photo gets committed to
`public_photos/` and served via `raw.githubusercontent.com` so Instagram's
API can fetch it — photos remain in git history even after being posted.
Don't use this for anything you don't want permanently public.

## How it works

1. You drop photos into a Google Drive folder — as many as you want, anytime.
2. 3x/day, a GitHub Actions workflow runs `scripts/post_to_instagram.py`,
   which:
   - Lists all photos in the Drive folder.
   - Excludes any photo used in the **last 10 posts** (`post_history.json`),
     so nothing repeats too soon. If the whole library is smaller than that,
     it just picks from everything.
   - For any photo it hasn't seen before, asks Claude to tag it (category,
     location, whether a person is in it) — cached in `photo_meta.json` so
     this only happens once per photo.
   - Looks for a themed group of 3+ eligible photos sharing a tag (e.g. same
     location, or same category) and, ~40% of the time when one exists,
     posts a **carousel/slideshow** of up to 4 photos instead of a single
     photo. Otherwise posts one photo. This mixes naturally over time.
   - Normalizes every photo to a JPEG and **pads (never crops)** it to fit
     Instagram's supported aspect ratio (4:5 to 1.91:1), using a blurred
     copy of the photo itself as the fill — so nothing gets cut off.
   - Sends the chosen photo(s) to Claude for one short, casual caption +
     hashtags covering the whole post.
   - Publishes to Instagram (single photo or carousel) via the Graph API.
   - Appends the post to `post_history.json`.

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

### 5. Adding photos

Just upload photos to the Drive folder whenever you want — via the Google
Drive app on your phone (`+` → Upload → Photos and Videos), the desktop
site, or drag-and-drop. No automation needed; the bot picks up whatever's
in the folder on its next scheduled run. The more photos you keep in there,
the more variety it has to work with for carousels and avoiding repeats.

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
