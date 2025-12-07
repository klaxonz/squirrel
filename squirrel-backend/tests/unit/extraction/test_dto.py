"""
DTO层单元测试
"""
import pytest
from datetime import datetime
from pydantic import ValidationError

from core.extraction.dto import ActorDTO, VideoDTO
from core.extraction.dto.validators import (
    validate_url,
    validate_not_empty,
    parse_publish_date,
    validate_duration,
)


class TestValidators:
    """测试验证器函数"""
    
    def test_validate_url_success(self):
        """测试URL验证 - 成功"""
        assert validate_url('https://example.com') == 'https://example.com'
        assert validate_url('http://example.com') == 'http://example.com'
        assert validate_url('  https://example.com  ') == 'https://example.com'
    
    def test_validate_url_failure(self):
        """测试URL验证 - 失败"""
        with pytest.raises(ValueError, match='must be a non-empty string'):
            validate_url('')
        
        with pytest.raises(ValueError, match='must start with'):
            validate_url('example.com')
        
        with pytest.raises(ValueError, match='cannot be empty'):
            validate_url('   ')
    
    def test_validate_not_empty_success(self):
        """测试非空验证 - 成功"""
        assert validate_not_empty('hello', 'Field') == 'hello'
        assert validate_not_empty('  hello  ', 'Field') == 'hello'
    
    def test_validate_not_empty_failure(self):
        """测试非空验证 - 失败"""
        with pytest.raises(ValueError, match='must be a non-empty string'):
            validate_not_empty('', 'Field')
        
        with pytest.raises(ValueError, match='cannot be empty'):
            validate_not_empty('   ', 'Field')
    
    def test_parse_publish_date_datetime(self):
        """测试日期解析 - datetime对象"""
        dt = datetime(2023, 12, 7, 15, 30, 45)
        assert parse_publish_date(dt) == dt
    
    def test_parse_publish_date_timestamp(self):
        """测试日期解析 - timestamp"""
        timestamp = 1701961845  # 2023-12-07 15:30:45
        result = parse_publish_date(timestamp)
        assert isinstance(result, datetime)
        assert result.year == 2023
        assert result.month == 12
    
    def test_parse_publish_date_string(self):
        """测试日期解析 - 字符串"""
        assert parse_publish_date('20231207').date() == datetime(2023, 12, 7).date()
        assert parse_publish_date('2023-12-07').date() == datetime(2023, 12, 7).date()
        assert parse_publish_date('2023/12/07').date() == datetime(2023, 12, 7).date()
        assert parse_publish_date('2023.12.07').date() == datetime(2023, 12, 7).date()
    
    def test_parse_publish_date_none(self):
        """测试日期解析 - None"""
        assert parse_publish_date(None) is None
        assert parse_publish_date('') is None
    
    def test_parse_publish_date_invalid(self):
        """测试日期解析 - 无效格式"""
        with pytest.raises(ValueError, match='Cannot parse publish_date'):
            parse_publish_date('invalid-date')
    
    def test_validate_duration_success(self):
        """测试时长验证 - 成功"""
        assert validate_duration(100) == 100
        assert validate_duration(0) == 0
        assert validate_duration(None) is None
    
    def test_validate_duration_failure(self):
        """测试时长验证 - 失败"""
        with pytest.raises(ValueError, match='must be an integer'):
            validate_duration('100')
        
        with pytest.raises(ValueError, match='must be non-negative'):
            validate_duration(-1)
        
        with pytest.raises(ValueError, match='seems unreasonable'):
            validate_duration(100000)


class TestActorDTO:
    """测试ActorDTO"""
    
    def test_create_actor_success(self):
        """测试创建Actor - 成功"""
        actor = ActorDTO(
            url='https://example.com/actor/123',
            name='Test Actor',
            avatar='https://example.com/avatar.jpg'
        )
        
        assert actor.url == 'https://example.com/actor/123'
        assert actor.name == 'Test Actor'
        assert actor.avatar == 'https://example.com/avatar.jpg'
    
    def test_create_actor_without_avatar(self):
        """测试创建Actor - 无头像"""
        actor = ActorDTO(
            url='https://example.com/actor/123',
            name='Test Actor'
        )
        
        assert actor.avatar is None
    
    def test_create_actor_invalid_url(self):
        """测试创建Actor - 无效URL"""
        with pytest.raises(ValidationError):
            ActorDTO(
                url='invalid-url',
                name='Test Actor'
            )
    
    def test_create_actor_empty_name(self):
        """测试创建Actor - 空名称"""
        with pytest.raises(ValidationError):
            ActorDTO(
                url='https://example.com/actor/123',
                name=''
            )
    
    def test_actor_immutable(self):
        """测试Actor不可变"""
        actor = ActorDTO(
            url='https://example.com/actor/123',
            name='Test Actor'
        )
        
        with pytest.raises(ValidationError):
            actor.name = 'New Name'
    
    def test_actor_to_dict(self):
        """测试Actor转字典"""
        actor = ActorDTO(
            url='https://example.com/actor/123',
            name='Test Actor',
            avatar='https://example.com/avatar.jpg'
        )
        
        data = actor.to_dict()
        assert data['url'] == 'https://example.com/actor/123'
        assert data['name'] == 'Test Actor'
        assert data['avatar'] == 'https://example.com/avatar.jpg'
    
    def test_actor_from_dict(self):
        """测试从字典创建Actor"""
        data = {
            'url': 'https://example.com/actor/123',
            'name': 'Test Actor',
            'avatar': 'https://example.com/avatar.jpg'
        }
        
        actor = ActorDTO.from_dict(data)
        assert actor.url == data['url']
        assert actor.name == data['name']
        assert actor.avatar == data['avatar']


class TestVideoDTO:
    """测试VideoDTO"""
    
    def test_create_video_minimal(self):
        """测试创建Video - 最小字段"""
        video = VideoDTO(
            url='https://example.com/video/123',
            title='Test Video',
            site_name='test_site'
        )
        
        assert video.url == 'https://example.com/video/123'
        assert video.title == 'Test Video'
        assert video.site_name == 'test_site'
        assert video.actors == []
        assert video.thumbnail is None
    
    def test_create_video_full(self):
        """测试创建Video - 完整字段"""
        actor = ActorDTO(
            url='https://example.com/actor/123',
            name='Test Actor'
        )
        
        video = VideoDTO(
            url='https://example.com/video/123',
            title='Test Video',
            site_name='test_site',
            thumbnail='https://example.com/thumb.jpg',
            duration=300,
            publish_date=datetime(2023, 12, 7),
            description='Test description',
            tags=['tag1', 'tag2'],
            actors=[actor]
        )
        
        assert video.duration == 300
        assert video.publish_date == datetime(2023, 12, 7)
        assert video.description == 'Test description'
        assert video.tags == ['tag1', 'tag2']
        assert len(video.actors) == 1
        assert video.actors[0].name == 'Test Actor'
    
    def test_create_video_parse_publish_date_timestamp(self):
        """测试创建Video - 解析timestamp"""
        video = VideoDTO(
            url='https://example.com/video/123',
            title='Test Video',
            site_name='test_site',
            publish_date=1701961845
        )
        
        assert isinstance(video.publish_date, datetime)
        assert video.publish_date.year == 2023
    
    def test_create_video_parse_publish_date_string(self):
        """测试创建Video - 解析字符串日期"""
        video = VideoDTO(
            url='https://example.com/video/123',
            title='Test Video',
            site_name='test_site',
            publish_date='2023-12-07'
        )
        
        assert isinstance(video.publish_date, datetime)
        assert video.publish_date.date() == datetime(2023, 12, 7).date()
    
    def test_create_video_invalid_url(self):
        """测试创建Video - 无效URL"""
        with pytest.raises(ValidationError):
            VideoDTO(
                url='invalid-url',
                title='Test Video',
                site_name='test_site'
            )
    
    def test_create_video_empty_title(self):
        """测试创建Video - 空标题"""
        with pytest.raises(ValidationError):
            VideoDTO(
                url='https://example.com/video/123',
                title='',
                site_name='test_site'
            )
    
    def test_create_video_negative_duration(self):
        """测试创建Video - 负数时长"""
        with pytest.raises(ValidationError):
            VideoDTO(
                url='https://example.com/video/123',
                title='Test Video',
                site_name='test_site',
                duration=-100
            )
    
    def test_video_clean_tags(self):
        """测试Video标签清理"""
        video = VideoDTO(
            url='https://example.com/video/123',
            title='Test Video',
            site_name='test_site',
            tags=['  tag1  ', 'tag2', '', '  ']
        )
        
        # 应该去除空标签和空白
        assert video.tags == ['tag1', 'tag2']
    
    def test_video_immutable(self):
        """测试Video不可变"""
        video = VideoDTO(
            url='https://example.com/video/123',
            title='Test Video',
            site_name='test_site'
        )
        
        with pytest.raises(ValidationError):
            video.title = 'New Title'
    
    def test_video_to_dict(self):
        """测试Video转字典"""
        actor = ActorDTO(
            url='https://example.com/actor/123',
            name='Test Actor'
        )
        
        video = VideoDTO(
            url='https://example.com/video/123',
            title='Test Video',
            site_name='test_site',
            duration=300,
            publish_date=datetime(2023, 12, 7, 15, 30, 45),
            actors=[actor]
        )
        
        data = video.to_dict()
        
        assert data['url'] == 'https://example.com/video/123'
        assert data['title'] == 'Test Video'
        assert data['duration'] == 300
        assert data['publish_date'] == '2023-12-07T15:30:45'
        assert len(data['actors']) == 1
        assert data['actors'][0]['name'] == 'Test Actor'
    
    def test_video_from_dict(self):
        """测试从字典创建Video"""
        data = {
            'url': 'https://example.com/video/123',
            'title': 'Test Video',
            'site_name': 'test_site',
            'duration': 300,
            'publish_date': '2023-12-07',
            'actors': [
                {
                    'url': 'https://example.com/actor/123',
                    'name': 'Test Actor'
                }
            ]
        }
        
        video = VideoDTO.from_dict(data)
        
        assert video.url == data['url']
        assert video.title == data['title']
        assert video.duration == 300
        assert len(video.actors) == 1
    
    def test_video_helper_methods(self):
        """测试Video辅助方法"""
        video = VideoDTO(
            url='https://example.com/video/123',
            title='Test Video',
            site_name='test_site',
            thumbnail='https://example.com/thumb.jpg',
            publish_date=datetime(2023, 12, 7),
            actors=[
                ActorDTO(url='https://example.com/actor/123', name='Actor 1')
            ]
        )
        
        assert video.has_actors() is True
        assert video.has_thumbnail() is True
        assert video.has_publish_date() is True
        
        summary = video.get_summary()
        assert 'Test Video' in summary
        assert 'actors=1' in summary
    
    def test_video_without_optional_fields(self):
        """测试Video - 无可选字段"""
        video = VideoDTO(
            url='https://example.com/video/123',
            title='Test Video',
            site_name='test_site'
        )
        
        assert video.has_actors() is False
        assert video.has_thumbnail() is False
        assert video.has_publish_date() is False
