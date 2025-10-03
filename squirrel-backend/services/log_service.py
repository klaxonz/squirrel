import os
import re
from typing import List, Dict, Optional, Tuple
from datetime import datetime

from common.log import LOG_DIR


def get_log_files() -> List[Dict[str, any]]:
    """获取所有日志文件列表"""
    if not os.path.exists(LOG_DIR):
        return []
    
    log_files = []
    for filename in os.listdir(LOG_DIR):
        if filename.endswith('.log'):
            filepath = os.path.join(LOG_DIR, filename)
            stat = os.stat(filepath)
            log_files.append({
                'name': filename,
                'size': stat.st_size,
                'modified_time': datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d %H:%M:%S')
            })
    
    log_files.sort(key=lambda x: x['name'], reverse=True)
    return log_files


def read_log_lines(
    filename: str = 'app.log',
    keyword: Optional[str] = None,
    level: Optional[str] = None,
    start_line: int = 0,
    limit: int = 500
) -> Tuple[List[Dict[str, any]], int, bool]:
    """
    读取日志文件内容
    
    Args:
        filename: 日志文件名
        keyword: 搜索关键词
        level: 日志级别过滤 (INFO, WARNING, ERROR, DEBUG)
        start_line: 起始行号
        limit: 返回的最大行数
    
    Returns:
        (日志行列表, 总行数, 是否还有更多)
    """
    filepath = os.path.join(LOG_DIR, filename)
    
    if not os.path.exists(filepath):
        return [], 0, False
    
    # 日志级别正则匹配
    log_pattern = re.compile(
        r'^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3}) (DEBUG|INFO|WARNING|ERROR|CRITICAL) (.+?): (.+)$'
    )
    
    all_lines = []
    filtered_lines = []
    
    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
        current_log_entry = None
        
        for line_num, line in enumerate(f, start=1):
            line = line.rstrip('\n')
            all_lines.append(line)
            
            # 尝试匹配新的日志条目
            match = log_pattern.match(line)
            
            if match:
                # 保存之前的日志条目
                if current_log_entry and _should_include_log(current_log_entry, keyword, level):
                    filtered_lines.append(current_log_entry)
                
                # 开始新的日志条目
                timestamp, log_level, logger_name, message = match.groups()
                current_log_entry = {
                    'line_num': line_num,
                    'timestamp': timestamp,
                    'level': log_level,
                    'logger': logger_name,
                    'message': message,
                    'raw_lines': [line]
                }
            else:
                # 多行日志的后续行（如堆栈信息）
                if current_log_entry:
                    current_log_entry['message'] += '\n' + line
                    current_log_entry['raw_lines'].append(line)
        
        # 处理最后一条日志
        if current_log_entry and _should_include_log(current_log_entry, keyword, level):
            filtered_lines.append(current_log_entry)
    
    total_count = len(filtered_lines)
    has_more = start_line + limit < total_count
    
    # 倒序显示（最新的在前）
    filtered_lines.reverse()
    
    # 分页
    result_lines = filtered_lines[start_line:start_line + limit]
    
    return result_lines, total_count, has_more


def _should_include_log(log_entry: Dict, keyword: Optional[str], level: Optional[str]) -> bool:
    """判断日志条目是否应该包含在结果中"""
    # 级别过滤
    if level and log_entry['level'] != level:
        return False
    
    # 关键词过滤
    if keyword:
        keyword_lower = keyword.lower()
        searchable_text = (
            log_entry['message'] + ' ' + 
            log_entry['logger'] + ' ' + 
            log_entry['level']
        ).lower()
        
        if keyword_lower not in searchable_text:
            return False
    
    return True


def get_latest_logs(limit: int = 100) -> List[Dict[str, any]]:
    """获取最新的日志条目（用于实时刷新）"""
    lines, _, _ = read_log_lines(
        filename='app.log',
        start_line=0,
        limit=limit
    )
    return lines


def tail_log_file(filename: str = 'app.log', lines: int = 100) -> List[str]:
    """获取日志文件的最后 N 行（类似 tail 命令）"""
    filepath = os.path.join(LOG_DIR, filename)
    
    if not os.path.exists(filepath):
        return []
    
    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
        all_lines = f.readlines()
        return [line.rstrip('\n') for line in all_lines[-lines:]]

