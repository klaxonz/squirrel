import os
import re
from datetime import datetime

from common.log import LOG_DIR


def get_log_files() -> list[dict[str, any]]:
    """获取所有日志文件列表"""
    if not os.path.exists(LOG_DIR):
        return []

    log_files = []
    for filename in os.listdir(LOG_DIR):
        if filename.endswith(".log"):
            filepath = os.path.join(LOG_DIR, filename)
            stat = os.stat(filepath)
            log_files.append({
                "name": filename,
                "size": stat.st_size,
                "modified_time": datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S"),
            })

    log_files.sort(key=lambda x: x["name"], reverse=True)
    return log_files


def read_log_lines(
    filename: str = "app.log",
    keyword: str | None = None,
    level: str | None = None,
    start_line: int = 0,
    limit: int = 500,
) -> tuple[list[dict[str, any]], int, bool]:
    """读取日志文件内容

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

    # 日志级别正则匹配 (支持新旧两种格式)
    # 新格式: 2025-10-03 10:30:45,123 [trace_id] INFO logger_name: message
    # 旧格式: 2025-10-03 10:30:45,123 INFO logger_name: message
    log_pattern_new = re.compile(
        r"^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3}) \[([^\]]+)\] (DEBUG|INFO|WARNING|ERROR|CRITICAL) (.+?): (.+)$",
    )
    log_pattern_old = re.compile(
        r"^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3}) (DEBUG|INFO|WARNING|ERROR|CRITICAL) (.+?): (.+)$",
    )

    all_lines = []
    filtered_lines = []

    with open(filepath, encoding="utf-8", errors="ignore") as f:
        current_log_entry = None

        for line_num, line in enumerate(f, start=1):
            line = line.rstrip("\n")
            all_lines.append(line)

            # 先尝试匹配新格式（带 trace_id）
            match = log_pattern_new.match(line)

            if match:
                # 保存之前的日志条目
                if current_log_entry and _should_include_log(current_log_entry, keyword, level):
                    filtered_lines.append(current_log_entry)

                # 开始新的日志条目（新格式）
                timestamp, trace_id, log_level, logger_name, message = match.groups()
                current_log_entry = {
                    "line_num": line_num,
                    "timestamp": timestamp,
                    "trace_id": trace_id if trace_id != "-" else None,
                    "level": log_level,
                    "logger": logger_name,
                    "message": message,
                    "raw_lines": [line],
                }
            else:
                # 尝试匹配旧格式（不带 trace_id）
                match = log_pattern_old.match(line)
                if match:
                    # 保存之前的日志条目
                    if current_log_entry and _should_include_log(current_log_entry, keyword, level):
                        filtered_lines.append(current_log_entry)

                    # 开始新的日志条目（旧格式）
                    timestamp, log_level, logger_name, message = match.groups()
                    current_log_entry = {
                        "line_num": line_num,
                        "timestamp": timestamp,
                        "trace_id": None,
                        "level": log_level,
                        "logger": logger_name,
                        "message": message,
                        "raw_lines": [line],
                    }
                # 多行日志的后续行（如堆栈信息）
                elif current_log_entry:
                    current_log_entry["message"] += "\n" + line
                    current_log_entry["raw_lines"].append(line)

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


def _should_include_log(log_entry: dict, keyword: str | None, level: str | None) -> bool:
    """判断日志条目是否应该包含在结果中"""
    # 级别过滤
    if level and log_entry["level"] != level:
        return False

    # 关键词过滤
    if keyword:
        keyword_lower = keyword.lower()
        searchable_text = (
            log_entry["message"] + " " +
            log_entry["logger"] + " " +
            log_entry["level"]
        ).lower()

        # 如果有 trace_id，也包含在搜索范围内
        if log_entry.get("trace_id"):
            searchable_text += " " + log_entry["trace_id"].lower()

        if keyword_lower not in searchable_text:
            return False

    return True

