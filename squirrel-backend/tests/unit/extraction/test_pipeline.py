"""
Pipeline单元测试
"""
import pytest
from unittest.mock import Mock
from datetime import datetime

from crawl import ExtractionTask, TaskPriority, Video, Actor
from core.extraction.pipeline import PipelineContext, PipelineStage, ExtractionPipeline
from core.extraction.pipeline.stages import ExtractionStage, ValidationStage
from core.extraction.dto import VideoDTO, ActorDTO
from core.extraction.adapters import PluginDataAdapter
from core.extraction.exceptions import ExtractionError


class TestPipelineContext:
    """测试PipelineContext"""
    
    def test_create_context(self):
        """测试创建上下文"""
        task = ExtractionTask(
            url='https://example.com/video/123',
            site_name='test_site'
        )
        
        context = PipelineContext(task=task)
        
        assert context.task == task
        assert context.plugin_video is None
        assert context.video_dto is None
        assert context.video_model is None
        assert context.current_stage == "init"
        assert context.errors == []
        assert context.should_skip_persistence is False
    
    def test_add_error(self):
        """测试添加错误"""
        task = ExtractionTask(
            url='https://example.com/video/123',
            site_name='test_site'
        )
        context = PipelineContext(task=task)
        
        context.add_error('test_stage', 'test error')
        
        assert context.has_errors()
        assert len(context.errors) == 1
        assert '[test_stage]' in context.errors[0]
    
    def test_get_duration(self):
        """测试获取执行时长"""
        task = ExtractionTask(
            url='https://example.com/video/123',
            site_name='test_site'
        )
        context = PipelineContext(task=task)
        
        import time
        time.sleep(0.1)
        
        duration = context.get_duration()
        assert duration >= 0.1
    
    def test_to_dict(self):
        """测试转换为字典"""
        task = ExtractionTask(
            url='https://example.com/video/123',
            site_name='test_site'
        )
        context = PipelineContext(task=task)
        context.current_stage = 'extraction'
        
        data = context.to_dict()
        
        assert data['task_id'] == task.task_id
        assert data['url'] == task.url
        assert data['current_stage'] == 'extraction'
        assert 'duration' in data


class TestExtractionStage:
    """测试ExtractionStage"""
    
    def test_extraction_success(self):
        """测试提取成功"""
        # Mock extractor
        mock_video = Mock(spec=Video)
        mock_video.url = 'https://example.com/video/123'
        mock_video.title = 'Test Video'
        
        mock_result = Mock()
        mock_result.success = True
        mock_result.data = mock_video
        
        mock_extractor = Mock()
        mock_extractor.extract.return_value = mock_result
        
        # Mock factory
        mock_factory = Mock()
        mock_factory.create_extractor.return_value = mock_extractor
        
        # Create stage
        stage = ExtractionStage(mock_factory)
        
        # Create context
        task = ExtractionTask(
            url='https://example.com/video/123',
            site_name='test_site'
        )
        context = PipelineContext(task=task)
        
        # Execute
        result_context = stage.execute(context)
        
        # Verify
        assert result_context.plugin_video == mock_video
        assert mock_extractor.extract.called
    
    def test_extraction_no_extractor(self):
        """测试没有提取器"""
        # Mock factory returning None
        mock_factory = Mock()
        mock_factory.create_extractor.return_value = None
        
        # Create stage
        stage = ExtractionStage(mock_factory)
        
        # Create context
        task = ExtractionTask(
            url='https://example.com/video/123',
            site_name='test_site'
        )
        context = PipelineContext(task=task)
        
        # Execute - should raise
        with pytest.raises(ExtractionError, match="No extractor found"):
            stage.execute(context)
    
    def test_extraction_failure(self):
        """测试提取失败"""
        # Mock failed result
        mock_result = Mock()
        mock_result.success = False
        mock_result.error = "Extraction failed"
        
        mock_extractor = Mock()
        mock_extractor.extract.return_value = mock_result
        
        mock_factory = Mock()
        mock_factory.create_extractor.return_value = mock_extractor
        
        # Create stage
        stage = ExtractionStage(mock_factory)
        
        # Create context
        task = ExtractionTask(
            url='https://example.com/video/123',
            site_name='test_site'
        )
        context = PipelineContext(task=task)
        
        # Execute - should raise
        with pytest.raises(ExtractionError, match="Extraction failed"):
            stage.execute(context)


class TestValidationStage:
    """测试ValidationStage"""
    
    def test_validation_success(self):
        """测试验证成功"""
        # Mock adapter
        mock_dto = VideoDTO(
            url='https://example.com/video/123',
            title='Test Video',
            site_name='test_site'
        )
        
        mock_adapter = Mock(spec=PluginDataAdapter)
        mock_adapter.adapt.return_value = mock_dto
        
        # Create stage
        stage = ValidationStage(mock_adapter)
        
        # Create context with plugin_video
        task = ExtractionTask(
            url='https://example.com/video/123',
            site_name='test_site'
        )
        context = PipelineContext(task=task)
        
        mock_video = Mock(spec=Video)
        context.plugin_video = mock_video
        
        # Execute
        result_context = stage.execute(context)
        
        # Verify
        assert result_context.video_dto == mock_dto
        assert mock_adapter.adapt.called
    
    def test_validation_no_plugin_video(self):
        """测试没有plugin_video"""
        mock_adapter = Mock(spec=PluginDataAdapter)
        stage = ValidationStage(mock_adapter)
        
        task = ExtractionTask(
            url='https://example.com/video/123',
            site_name='test_site'
        )
        context = PipelineContext(task=task)
        # plugin_video is None
        
        # Execute - should raise
        with pytest.raises(Exception, match="No plugin video data"):
            stage.execute(context)
    
    def test_validation_can_skip(self):
        """测试已有video_dto可跳过"""
        mock_adapter = Mock(spec=PluginDataAdapter)
        stage = ValidationStage(mock_adapter)
        
        task = ExtractionTask(
            url='https://example.com/video/123',
            site_name='test_site'
        )
        context = PipelineContext(task=task)
        
        # 没有video_dto，不能跳过
        assert stage.can_skip(context) is False
        
        # 有video_dto，可以跳过
        context.video_dto = Mock()
        assert stage.can_skip(context) is True


class TestExtractionPipeline:
    """测试ExtractionPipeline"""
    
    def test_pipeline_execute_all_stages(self):
        """测试Pipeline执行所有Stage"""
        # Create context
        task = ExtractionTask(
            url='https://example.com/video/123',
            site_name='test_site'
        )
        context = PipelineContext(task=task)
        context.video_dto = VideoDTO(
            url='https://example.com/video/123',
            title='Test',
            site_name='test_site'
        )
        
        # Mock stages - return the same context
        stage1 = Mock(spec=PipelineStage)
        stage1.stage_name = 'stage1'
        stage1.can_skip.return_value = False
        stage1.execute.return_value = context  # Return same context
        
        stage2 = Mock(spec=PipelineStage)
        stage2.stage_name = 'stage2'
        stage2.can_skip.return_value = False
        stage2.execute.return_value = context  # Return same context
        
        # Create pipeline
        pipeline = ExtractionPipeline([stage1, stage2])
        
        # Execute
        result = pipeline.execute(context)
        
        # Verify
        assert result.success is True
        assert stage1.execute.called
        assert stage2.execute.called
    
    def test_pipeline_skip_stage(self):
        """测试Pipeline跳过Stage"""
        # Create context
        task = ExtractionTask(
            url='https://example.com/video/123',
            site_name='test_site'
        )
        context = PipelineContext(task=task)
        context.video_dto = VideoDTO(
            url='https://example.com/video/123',
            title='Test',
            site_name='test_site'
        )
        
        # Stage that should be skipped
        skipped_stage = Mock(spec=PipelineStage)
        skipped_stage.stage_name = 'skipped'
        skipped_stage.can_skip.return_value = True
        
        # Stage that should execute
        executed_stage = Mock(spec=PipelineStage)
        executed_stage.stage_name = 'executed'
        executed_stage.can_skip.return_value = False
        executed_stage.execute.return_value = context  # Return same context
        
        # Create pipeline
        pipeline = ExtractionPipeline([skipped_stage, executed_stage])
        
        # Execute
        result = pipeline.execute(context)
        
        # Verify
        assert result.success is True
        assert not skipped_stage.execute.called  # Skipped
        assert executed_stage.execute.called      # Executed
    
    def test_pipeline_stage_failure(self):
        """测试Stage失败"""
        # Failing stage
        failing_stage = Mock(spec=PipelineStage)
        failing_stage.stage_name = 'extraction'  # Critical stage
        failing_stage.can_skip.return_value = False
        failing_stage.execute.side_effect = Exception("Stage failed")
        failing_stage.on_error = Mock()
        
        # Create pipeline
        pipeline = ExtractionPipeline([failing_stage])
        
        # Create context
        task = ExtractionTask(
            url='https://example.com/video/123',
            site_name='test_site'
        )
        context = PipelineContext(task=task)
        
        # Execute
        result = pipeline.execute(context)
        
        # Verify
        assert result.success is False
        assert failing_stage.on_error.called
    
    def test_get_stage_names(self):
        """测试获取Stage名称"""
        stage1 = Mock(spec=PipelineStage)
        stage1.stage_name = 'extraction'
        
        stage2 = Mock(spec=PipelineStage)
        stage2.stage_name = 'validation'
        
        pipeline = ExtractionPipeline([stage1, stage2])
        
        names = pipeline.get_stage_names()
        
        assert names == ['extraction', 'validation']
