import io
import json

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload

SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]


def get_drive_service(service_account_json):
    info = json.loads(service_account_json)
    credentials = service_account.Credentials.from_service_account_info(info, scopes=SCOPES)
    return build("drive", "v3", credentials=credentials)


def list_photos(service, folder_id):
    query = f"'{folder_id}' in parents and trashed = false and mimeType contains 'image/'"
    response = service.files().list(
        q=query,
        orderBy="createdTime",
        fields="files(id, name, mimeType, createdTime)",
        pageSize=1000,
    ).execute()
    return response.get("files", [])


def download_file(service, file_id):
    request = service.files().get_media(fileId=file_id)
    buffer = io.BytesIO()
    downloader = MediaIoBaseDownload(buffer, request)
    done = False
    while not done:
        _, done = downloader.next_chunk()
    return buffer.getvalue()
