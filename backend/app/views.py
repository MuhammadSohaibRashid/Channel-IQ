import os
from django.http import JsonResponse
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from urllib.parse import urlparse, parse_qs
import boto3
import yt_dlp
import logging
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt

logger = logging.getLogger(__name__)

# Ensure the YouTube API key is set in environment variables
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")
if not YOUTUBE_API_KEY:
    raise ValueError("YouTube API Key not set. Please configure it in environment variables.")

# Extract Video ID from URL
def extract_video_id(video_url):
    try:
        parsed_url = urlparse(video_url)
        if parsed_url.netloc in ["www.youtube.com", "youtube.com"]:
            query_params = parse_qs(parsed_url.query)
            return query_params.get("v", [None])[0]
        elif parsed_url.netloc == "youtu.be":
            return parsed_url.path.strip("/")
        return None
    except Exception as e:
        logger.error(f"Error extracting video ID: {e}")
        return None

# Fetch Video Metadata
@csrf_exempt
def fetch_video_data(request):
    video_url = request.GET.get("url")
    if not video_url:
        return JsonResponse({"error": "No URL provided"}, status=400)

    video_id = extract_video_id(video_url)
    if not video_id:
        return JsonResponse({"error": "Invalid YouTube URL"}, status=400)

    try:
        youtube = build("youtube", "v3", developerKey=YOUTUBE_API_KEY)
        response = youtube.videos().list(part="snippet", id=video_id).execute()

        if "items" not in response or not response["items"]:
            return JsonResponse({"error": "Video not found"}, status=404)

        video_data = response["items"][0]["snippet"]
        return JsonResponse({
            "title": video_data["title"],
            "thumbnail": video_data["thumbnails"]["high"]["url"],
        })

    except HttpError as e:
        logger.error(f"Error fetching video metadata: {e}")
        return JsonResponse({"error": f"Error fetching video metadata: {e}"}, status=500)
    except Exception as e:
        logger.error(f"An unexpected error occurred: {e}")
        return JsonResponse({"error": f"An unexpected error occurred: {e}"}, status=500)

# Download Video and Upload to S3
@csrf_exempt
def download_video(request):
    if request.method == "POST":
        video_url = request.POST.get("url")
    else:
        video_url = request.GET.get("url")

    if not video_url:
        return JsonResponse({"error": "No URL provided"}, status=400)

    video_id = extract_video_id(video_url)
    if not video_id:
        return JsonResponse({"error": "Invalid YouTube URL"}, status=400)

    downloaded_file = f"/tmp/{video_id}.mp4"
    try:
        ydl_opts = {
            'format': 'best',
            'outtmpl': downloaded_file,
            'quiet': False,
            'logger': logger,
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            logger.debug(f"Downloading video: {video_url}")
            ydl.download([video_url])

        if not os.path.exists(downloaded_file):
            return JsonResponse({"error": "Downloaded file not found."}, status=500)

        s3_client = boto3.client(
            's3',
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY
        )
        s3_key = f"videos/{video_id}.mp4"
        logger.debug(f"Uploading to S3 bucket: {settings.AWS_STORAGE_BUCKET_NAME}, key: {s3_key}")
        s3_client.upload_file(downloaded_file, settings.AWS_STORAGE_BUCKET_NAME, s3_key)

        os.remove(downloaded_file)

        video_url_s3 = f"https://{settings.AWS_STORAGE_BUCKET_NAME}.s3.amazonaws.com/{s3_key}"
        return JsonResponse({"message": "Video uploaded successfully.", "url": video_url_s3})

    except yt_dlp.utils.DownloadError as e:
        logger.error(f"Download failed: {str(e)}")
        return JsonResponse({"error": f"Download error: {str(e)}"}, status=500)
    except boto3.exceptions.S3UploadFailedError as e:
        logger.error(f"S3 upload failed: {str(e)}")
        return JsonResponse({"error": f"S3 upload failed: {str(e)}"}, status=500)
    except Exception as e:
        logger.exception("Unexpected error occurred")
        return JsonResponse({"error": f"Unexpected error: {str(e)}"}, status=500)
    finally:
        if os.path.exists(downloaded_file):
            try:
                os.remove(downloaded_file)
            except Exception as e:
                logger.error(f"Failed to clean up file: {downloaded_file}, Error: {str(e)}")
