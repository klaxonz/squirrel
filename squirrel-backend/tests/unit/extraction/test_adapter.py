"""
Adapter层单元测试
"""
import pytest
from datetime import datetime
from unittest.mock import Mock, PropertyMock

from crawl import Video, Actor
from core.extraction.adapters import PluginDataAdapter
from core.extraction.dto import VideoDTO, ActorDTO
from core.extraction.exceptions import DataTransformError


class TestPluginDataAdapter:
    """测试PluginDataAdapter"""
    
    def setup_method(self):
        """每个测试前执行"""
        self.adapter = PluginDataAdapter()
    
    def test_adapt_minimal_video(self):
        """测试适配最小Video对象"""
        # 创建Mock Video
        mock_video = Mock(spec=Video)
        mock_video.url = 'https://example.com/video/123'
        mock_video.title = 'Test Video'
        mock_video.thumbnail = None
        mock_video.duration = None
        mock_video.actors = []
        
        # 执行适配
        dto = self.adapter.adapt(mock_video, 'test_site')
        
        # 验证
        assert isinstance(dto, VideoDTO)
        assert dto.url == 'https://example.com/video/123'
        assert dto.title == 'Test Video'
        assert dto.site_name == 'test_site'
        assert dto.actors == []
    
    def test_adapt_full_video(self):
        """测试适配完整Video对象"""
        # 创建Mock Actor
        mock_actor = Mock(spec=Actor)
        mock_actor.url = 'https://example.com/actor/123'
        mock_actor.name = 'Test Actor'
        mock_actor.avatar = 'https://example.com/avatar.jpg'
        
        # 创建Mock Video
        mock_video = Mock(spec=Video)
        mock_video.url = 'https://example.com/video/123'
        mock_video.title = 'Test Video'
        mock_video.thumbnail = 'https://example.com/thumb.jpg'
        mock_video.duration = 300
        mock_video.description = 'Test description'
        mock_video.tags = ['tag1', 'tag2']
        mock_video.publish_date = datetime(2023, 12, 7)
        mock_video.actors = [mock_actor]
        
        # 执行适配
        dto = self.adapter.adapt(mock_video, 'test_site')
        
        # 验证
        assert dto.url == 'https://example.com/video/123'
        assert dto.title == 'Test Video'
        assert dto.thumbnail == 'https://example.com/thumb.jpg'
        assert dto.duration == 300
        assert dto.description == 'Test description'
        assert dto.tags == ['tag1', 'tag2']
        assert dto.publish_date == datetime(2023, 12, 7)
        assert len(dto.actors) == 1
        assert dto.actors[0].name == 'Test Actor'
    
    def test_adapt_video_with_upload_date(self):
        """测试使用upload_date的Video"""
        mock_video = Mock(spec=Video)
        mock_video.url = 'https://example.com/video/123'
        mock_video.title = 'Test Video'
        mock_video.publish_date = None
        mock_video.upload_date = datetime(2023, 12, 7)
        mock_video.actors = []
        
        dto = self.adapter.adapt(mock_video, 'test_site')
        
        # 应该使用upload_date
        assert dto.publish_date == datetime(2023, 12, 7)
    
    def test_adapt_video_with_lazy_loading_actors(self):
        """测试懒加载actors的Video"""
        # 创建Mock Actor
        mock_actor = Mock(spec=Actor)
        mock_actor.url = 'https://example.com/actor/123'
        mock_actor.name = 'Test Actor'
        mock_actor.avatar = None
        
        # 创建Mock Video with lazy actors
        mock_video = Mock(spec=Video)
        mock_video.url = 'https://example.com/video/123'
        mock_video.title = 'Test Video'
        
        # 模拟懒加载：第一次访问actors时触发
        type(mock_video).actors = PropertyMock(return_value=[mock_actor])
        
        # 执行适配
        dto = self.adapter.adapt(mock_video, 'test_site')
        
        # 验证actors被正确提取
        assert len(dto.actors) == 1
        assert dto.actors[0].name == 'Test Actor'
    
    def test_adapt_video_actors_failure_should_not_break(self):
        """测试actors获取失败不应中断流程"""
        mock_video = Mock(spec=Video)
        mock_video.url = 'https://example.com/video/123'
        mock_video.title = 'Test Video'
        
        # 模拟actors访问失败（如HTTP请求失败）
        type(mock_video).actors = PropertyMock(
            side_effect=Exception("Network error")
        )
        
        # 执行适配（不应抛出异常）
        dto = self.adapter.adapt(mock_video, 'test_site')
        
        # 验证video仍然成功创建，只是没有actors
        assert dto.url == 'https://example.com/video/123'
        assert dto.title == 'Test Video'
        assert dto.actors == []
    
    def test_adapt_video_invalid_actor_should_skip(self):
        """测试无效的actor应该跳过"""
        # 创建Mock Actors（一个有效，一个无效）
        valid_actor = Mock(spec=Actor)
        valid_actor.url = 'https://example.com/actor/valid'
        valid_actor.name = 'Valid Actor'
        valid_actor.avatar = None
        
        invalid_actor = Mock(spec=Actor)
        invalid_actor.url = None  # 无效：缺少URL
        invalid_actor.name = 'Invalid Actor'
        
        # 创建Mock Video
        mock_video = Mock(spec=Video)
        mock_video.url = 'https://example.com/video/123'
        mock_video.title = 'Test Video'
        mock_video.actors = [valid_actor, invalid_actor]
        
        # 执行适配
        dto = self.adapter.adapt(mock_video, 'test_site')
        
        # 验证只有有效的actor被保留
        assert len(dto.actors) == 1
        assert dto.actors[0].name == 'Valid Actor'
    
    def test_adapt_video_missing_required_field(self):
        """测试缺少必填字段应该抛出异常"""
        mock_video = Mock(spec=Video)
        mock_video.url = 'https://example.com/video/123'
        mock_video.title = ''  # 空标题（不合法）
        mock_video.actors = []
        
        # 应该抛出DataTransformError
        with pytest.raises(DataTransformError):
            self.adapter.adapt(mock_video, 'test_site')
    
    def test_adapt_video_invalid_url(self):
        """测试无效URL应该抛出异常"""
        mock_video = Mock(spec=Video)
        mock_video.url = 'invalid-url'  # 无效URL
        mock_video.title = 'Test Video'
        mock_video.actors = []
        
        # 应该抛出DataTransformError
        with pytest.raises(DataTransformError):
            self.adapter.adapt(mock_video, 'test_site')
    
    def test_adapt_preserves_raw_data(self):
        """测试保留原始数据"""
        mock_video = Mock(spec=Video)
        mock_video.url = 'https://example.com/video/123'
        mock_video.title = 'Test Video'
        mock_video._base_info = {
            'original_field': 'value',
            'numeric_field': 123
        }
        mock_video.DOMAIN = 'example.com'
        mock_video.actors = []
        
        dto = self.adapter.adapt(mock_video, 'test_site')
        
        # 验证raw_data被保留
        assert dto.raw_data is not None
        assert 'base_info' in dto.raw_data
        assert dto.raw_data['base_info']['original_field'] == 'value'
        assert dto.raw_data['domain'] == 'example.com'
    
    def test_convert_actor_success(self):
        """测试转换Actor成功"""
        mock_actor = Mock(spec=Actor)
        mock_actor.url = 'https://example.com/actor/123'
        mock_actor.name = 'Test Actor'
        mock_actor.avatar = 'https://example.com/avatar.jpg'
        
        actor_dto = self.adapter._convert_actor(mock_actor)
        
        assert actor_dto is not None
        assert actor_dto.url == 'https://example.com/actor/123'
        assert actor_dto.name == 'Test Actor'
        assert actor_dto.avatar == 'https://example.com/avatar.jpg'
    
    def test_convert_actor_missing_url(self):
        """测试缺少URL的Actor应该返回None"""
        mock_actor = Mock(spec=Actor)
        mock_actor.url = None
        mock_actor.name = 'Test Actor'
        
        actor_dto = self.adapter._convert_actor(mock_actor)
        
        assert actor_dto is None
    
    def test_convert_actor_missing_name(self):
        """测试缺少name的Actor应该返回None"""
        mock_actor = Mock(spec=Actor)
        mock_actor.url = 'https://example.com/actor/123'
        mock_actor.name = None
        
        actor_dto = self.adapter._convert_actor(mock_actor)
        
        assert actor_dto is None
    
    def test_convert_actor_not_actor_instance(self):
        """测试非Actor对象应该返回None"""
        not_an_actor = "Not an actor object"
        
        actor_dto = self.adapter._convert_actor(not_an_actor)
        
        assert actor_dto is None
