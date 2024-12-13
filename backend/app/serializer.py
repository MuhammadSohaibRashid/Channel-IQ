from rest_framework import serializers
from . models import *

class VideoFetchSerializer(serializers.Serializer):
    video_url = serializers.URLField(required=True)

    def validate_video_url(self, value):
        # Validate if the URL is a YouTube video URL
        import re
        pattern = r"(https?://)?(www\.)?(youtube\.com|youtu\.be)/(watch\?v=)?([a-zA-Z0-9_-]{11})"
        if not re.match(pattern, value):
            raise serializers.ValidationError("Invalid YouTube URL.")
        return value
