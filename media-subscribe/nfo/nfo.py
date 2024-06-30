import os

from jinja2 import Environment, FileSystemLoader
from contextlib import suppress
from meta.video import Video


class NfoGenerator:
    PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    TEMPLATE_DIR = os.path.join(PROJECT_ROOT, 'templates/nfo')
    TEMPLATE_ENV = Environment(loader=FileSystemLoader(TEMPLATE_DIR))

    @staticmethod
    def _write_nfo_file(content, file_path):
        """辅助方法，用于写入NFO文件"""
        with suppress(FileExistsError):  # 忽略文件已存在的异常
            with open(file_path, 'w', encoding='utf-8') as nfo_file:
                nfo_file.write(content)

    @staticmethod
    def generate_tv_show_nfo(video: Video):
        uploader = video.get_uploader()
        uploader_id = uploader.get_id()
        uploader_name = uploader.get_name()
        tags = uploader.get_tags()

        template = NfoGenerator.TEMPLATE_ENV.get_template('tv_show_nfo.xml')
        nfo_content = template.render(
            uploader_id=uploader_id,
            uploader_name=uploader_name,
            tags=tags
        )

        download_path = video.get_tv_show_root_path()
        download_full_path = f"{download_path}/tvshow.nfo"
        NfoGenerator._write_nfo_file(nfo_content, download_full_path)

    @staticmethod
    def generate_episode_nfo(video: Video):
        uploader = video.get_uploader()
        template = NfoGenerator.TEMPLATE_ENV.get_template('episode_nfo.xml')
        nfo_content = template.render(
            series_title=uploader.get_name(),
            season=video.get_season(),
            episode_title=video.get_title(),
            description=video.get_description(),
            thumbnail_path=video.get_thumbnail()
        )

        download_path = video.get_download_full_path()
        filename = video.get_valid_filename()
        download_full_path = f"{download_path}/{filename}.nfo"
        NfoGenerator._write_nfo_file(nfo_content, download_full_path)

    @staticmethod
    def generate_nfo(video: Video):
        NfoGenerator.generate_tv_show_nfo(video)
        NfoGenerator.generate_episode_nfo(video)
