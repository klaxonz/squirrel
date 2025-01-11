import os
from contextlib import suppress

from jinja2 import Environment, FileSystemLoader

from core import download_config


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
    def generate_tv_show_nfo(subscription_name: str):
        template = NfoGenerator.TEMPLATE_ENV.get_template('tv_show_nfo.xml')
        nfo_content = template.render(
            uploader_name=subscription_name,
        )
        download_path = download_config.get_tv_show_root_path(subscription_name)
        download_full_path = f"{download_path}/tvshow.nfo"
        NfoGenerator._write_nfo_file(nfo_content, download_full_path)

    @staticmethod
    def generate_episode_nfo(subscription_name, title, description, thumbnail_path, season):
        template = NfoGenerator.TEMPLATE_ENV.get_template('episode_nfo.xml')
        nfo_content = template.render(
            series_title=subscription_name,
            season=season,
            episode_title=title,
            description=description,
            thumbnail_path=thumbnail_path
        )

        download_path = download_config.get_download_full_path(subscription_name, season)
        filename = download_config.get_valid_filename(title)
        download_full_path = f"{download_path}/{filename}.nfo"
        NfoGenerator._write_nfo_file(nfo_content, download_full_path)

    @staticmethod
    def generate_nfo(subscription_name, title, description, thumbnail_path, season):
        NfoGenerator.generate_tv_show_nfo(subscription_name)
        NfoGenerator.generate_episode_nfo(subscription_name, title, description, thumbnail_path, season)
