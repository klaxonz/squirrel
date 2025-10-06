from __future__ import annotations

from xml.etree import ElementTree as ET
from urllib.parse import quote
import re
import struct
import json
import subprocess
import logging
import yt_dlp

from crawl import (
    BaseMpdBuilder, 
    register_mpd, 
    get_http_session,
    filter_cookies_to_query_string,
    resolve_cookie_file_path
)

logger = logging.getLogger()

USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115 Safari/537.36'
SESSION = get_http_session()



def _proxy(u: str) -> str:
    return f"/api/video/proxy?domain=youtube.com&url=" + quote(u, safe='')


def _extract_video_info_with_ytdlp(url: str) -> dict:
    """
    使用 yt-dlp 提取视频信息，支持 cookies 认证
    """
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'skip_download': True,
        'noplaylist': True,
        'extract_flat': False,
    }
    
    # 优先使用 cookie 文件
    cookie_file = resolve_cookie_file_path(url)
    if cookie_file:
        logger.info(f"使用 cookie 文件: {cookie_file}")
        ydl_opts['cookiefile'] = cookie_file
    else:
        cookies = filter_cookies_to_query_string(url)
        if cookies:
            logger.info("使用字符串形式的 cookies")
            ydl_opts['cookie'] = cookies
        else:
            logger.warning("未找到 cookies，某些视频可能无法访问")
    
    try:
        logger.info(f"开始提取视频信息...")
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            logger.info(f"视频信息提取成功")
            return info
    except Exception as e:
        logger.error(f"yt-dlp 提取视频信息失败: {e}")
        raise

@register_mpd
class YouTubeMpdBuilder(BaseMpdBuilder):
    domain = 'youtube.com'

    def build_mpd(self, video) -> str:
        logger.info(f"使用 yt-dlp 提取视频信息: {video.url}")
        
        try:
            info = _extract_video_info_with_ytdlp(video.url)
        except Exception as e:
            logger.error(f"yt-dlp 提取失败: {e}")
            raise Exception(f"无法获取视频信息: {e}")
        
        duration = info.get('duration', 0)
        formats = info.get('formats', [])
        
        # 收集视频和音频流
        video_streams = []
        audio_streams = []
        
        for fmt in formats:
            vcodec = fmt.get('vcodec', 'none')
            acodec = fmt.get('acodec', 'none')
            url = fmt.get('url')
            
            if not url:
                continue
            
            # 只处理 adaptive 格式（纯视频或纯音频）
            if vcodec != 'none' and acodec != 'none':
                continue
            
            # 只处理 mp4 容器
            ext = fmt.get('ext', '')
            if ext not in ['mp4', 'm4a']:
                continue
            
            # 从 yt-dlp 提取完整的格式信息
            codec_str = vcodec if vcodec != 'none' else acodec
            
            # 过滤掉 AV1 编解码器（很多浏览器支持不完善，容易导致播放失败）
            # AV1 codec 通常以 av01 开头
            if codec_str and codec_str.lower().startswith('av01'):
                logger.debug(f"跳过 AV1 编解码器流: {fmt.get('format_id')} (codec: {codec_str})")
                continue
            
            format_info = {
                'id': fmt.get('format_id', ''),
                'url': url,
                'mime': f"{'video' if vcodec != 'none' else 'audio'}/mp4",
                'codecs': codec_str,
                'bandwidth': int(fmt.get('tbr', 0) * 1000) if fmt.get('tbr') else None,
                'width': fmt.get('width'),
                'height': fmt.get('height'),
                'fps': fmt.get('fps'),
                'audioSamplingRate': fmt.get('asr'),
                'audioChannels': fmt.get('audio_channels', 2),
                'language': fmt.get('language'),
                'format_note': fmt.get('format_note'),
            }
            
            # 检查是否有 fragment 信息（YouTube DASH）
            fragments = fmt.get('fragments')
            if fragments:
                # 有 fragments 表示这是分段流
                format_info['has_fragments'] = True
            
            if vcodec != 'none':
                video_streams.append(format_info)
            else:
                audio_streams.append(format_info)
        
        logger.info(f"找到 {len(video_streams)} 个视频流, {len(audio_streams)} 个音频流")
        
        # 构建 MPD
        mpd = ET.Element('MPD', xmlns='urn:mpeg:dash:schema:mpd:2011')
        mpd.set('type', 'static')
        mpd.set('profiles', 'urn:mpeg:dash:profile:isoff-on-demand:2011')
        if duration:
            mpd.set('mediaPresentationDuration', f"PT{int(duration)}S")
        mpd.set('minBufferTime', 'PT4S')
        
        period = ET.SubElement(mpd, 'Period', start='PT0S')

        # 添加视频流
        if video_streams:
            # 按分辨率和比特率排序
            video_streams.sort(key=lambda s: (s.get('height') or 0, s.get('bandwidth') or 0), reverse=True)
            
            video_as = ET.SubElement(period, 'AdaptationSet', contentType='video', segmentAlignment='true', mimeType='video/mp4')
            for stream in video_streams:
                rep = ET.SubElement(video_as, 'Representation', id=stream['id'])
                
                if stream.get('codecs'):
                    rep.set('codecs', stream['codecs'])
                if stream.get('bandwidth'):
                    rep.set('bandwidth', str(stream['bandwidth']))
                if stream.get('width'):
                    rep.set('width', str(stream['width']))
                if stream.get('height'):
                    rep.set('height', str(stream['height']))
                if stream.get('fps'):
                    rep.set('frameRate', str(stream['fps']))
                
                # BaseURL - 通过代理访问
                base_url = ET.SubElement(rep, 'BaseURL')
                base_url.text = _proxy(stream['url'])
                
                # SegmentBase - 告诉播放器这是一个单文件 DASH 流
                # 注意：不添加 Initialization 标签，让 dash.js 自动探测
                # 空的 <Initialization /> 会导致播放器不知道如何获取初始化段
                ET.SubElement(rep, 'SegmentBase')
        
        # 添加音频流（只添加第一个）
        if audio_streams:
            # 按比特率排序，选择最佳质量
            audio_streams.sort(key=lambda s: s.get('bandwidth') or 0, reverse=True)
            audio = audio_streams[0]
            
            audio_as = ET.SubElement(period, 'AdaptationSet', contentType='audio', segmentAlignment='true', mimeType='audio/mp4')
            rep = ET.SubElement(audio_as, 'Representation', id=audio['id'])
            
            if audio.get('codecs'):
                rep.set('codecs', audio['codecs'])
            if audio.get('bandwidth'):
                rep.set('bandwidth', str(audio['bandwidth']))
            if audio.get('audioSamplingRate'):
                rep.set('audioSamplingRate', str(audio['audioSamplingRate']))
            if audio.get('language'):
                rep.set('{http://www.w3.org/XML/1998/namespace}lang', audio['language'])
            
            # 音频通道配置
            if audio.get('audioChannels'):
                audio_ch_config = ET.SubElement(rep, 'AudioChannelConfiguration')
                audio_ch_config.set('schemeIdUri', 'urn:mpeg:dash:23003:3:audio_channel_configuration:2011')
                audio_ch_config.set('value', str(audio['audioChannels']))
            
            # BaseURL - 通过代理访问
            base_url = ET.SubElement(rep, 'BaseURL')
            base_url.text = _proxy(audio['url'])
            
            # SegmentBase - 不添加 Initialization 标签，让 dash.js 自动探测
            ET.SubElement(rep, 'SegmentBase')
        
        return ET.tostring(mpd, encoding='unicode')


