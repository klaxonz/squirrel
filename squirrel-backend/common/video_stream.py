import os
import re
import stat
from email.utils import formatdate
from mimetypes import guess_type
from starlette.requests import Request
from starlette.responses import StreamingResponse


class VideoStreamHandler:
    CHUNK_SIZE = 1024 * 1024  # 1MB
    SUPPORTED_EXTENSIONS = ['.mp4', '.mkv', '.webm']

    @staticmethod
    def find_video_file(output_dir: str, filename: str) -> str:
        files = os.listdir(output_dir)
        for file in files:
            if file.startswith(filename) and any(file.endswith(ext) for ext in VideoStreamHandler.SUPPORTED_EXTENSIONS):
                return os.path.join(output_dir, file)
        return None

    @staticmethod
    def create_stream_response(request: Request, video_path: str) -> StreamingResponse:
        stat_result = os.stat(video_path)
        content_type, _ = guess_type(video_path)
        content_type = content_type or 'application/octet-stream'

        # Parse range header
        range_str = request.headers.get('range', '')
        range_match = re.search(r'bytes=(\d+)-(\d+)', range_str, re.S) or re.search(r'bytes=(\d+)-', range_str, re.S)

        if range_match:
            start_bytes = int(range_match.group(1))
            end_bytes = int(range_match.group(2)) if range_match.lastindex == 2 else stat_result.st_size - 1
        else:
            start_bytes = 0
            end_bytes = stat_result.st_size - 1

        content_length = stat_result.st_size - start_bytes if stat.S_ISREG(stat_result.st_mode) else stat_result.st_size

        return StreamingResponse(
            VideoStreamHandler._file_iterator(video_path, start_bytes),
            media_type=content_type,
            headers={
                'accept-ranges': 'bytes',
                'connection': 'keep-alive',
                'content-length': str(content_length),
                'content-range': f'bytes {start_bytes}-{end_bytes}/{stat_result.st_size}',
                'last-modified': formatdate(stat_result.st_mtime, usegmt=True),
            },
            status_code=206 if start_bytes > 0 else 200
        )

    @staticmethod
    def _file_iterator(file_path: str, offset: int):
        with open(file_path, 'rb') as f:
            f.seek(offset, os.SEEK_SET)
            while True:
                data = f.read(VideoStreamHandler.CHUNK_SIZE)
                if not data:
                    break
                yield data
