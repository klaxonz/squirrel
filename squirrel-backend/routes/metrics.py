"""
监控指标 API 路由

提供指标查询、实时监控和健康评估接口。
"""
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from fastapi import APIRouter, Query, HTTPException
from pydantic import BaseModel, Field

from utils.metrics import metrics
from services.metrics_service import metrics_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/metrics", tags=["Metrics"])


# ==================== 辅助函数 ====================

def _parse_redis_key(key: str) -> Dict[str, Any]:
    """解析 Redis key 提取指标信息
    
    Key 格式：metrics:{type}:{name}:{tags}:{window}:{minute}
    注意：tags 中的值可能包含冒号（如队列名 video_extract:bilibili:incr）
    """
    try:
        if isinstance(key, bytes):
            key = key.decode('utf-8')
        
        # 前三部分是固定的：metrics, type, name
        # 第四部分是 tags，可能包含冒号
        # 后续部分是 window 信息
        
        # 先按 : 分割，找到 tags 部分
        parts = key.split(":")
        if len(parts) < 4:
            return {}
        
        metric_type = parts[1]
        metric_name = parts[2]
        
        # tags 部分：从 parts[3] 开始，到遇到时间窗口标识（1m, total）结束
        # 或者如果是 gauge 类型，没有时间窗口
        tags = {}
        tags_parts = []
        window_start_idx = 3
        
        for i in range(3, len(parts)):
            part = parts[i]
            # 检查是否是时间窗口部分
            if part in ("1m", "total") or (len(part) == 12 and part.isdigit()):
                window_start_idx = i
                break
            tags_parts.append(part)
        
        if tags_parts:
            tags_str = ":".join(tags_parts)
            if tags_str != "_":
                for pair in tags_str.split(","):
                    if "=" in pair:
                        k, v = pair.split("=", 1)
                        tags[k] = v
        
        return {
            "type": metric_type,
            "name": metric_name,
            "tags": tags
        }
    except Exception:
        pass
    return {}


def _get_all_counters_by_pattern(pattern: str) -> List[Dict[str, Any]]:
    """获取匹配模式的所有计数器及其值"""
    results = []
    keys = metrics.get_metrics_keys_by_pattern(pattern)
    for key in keys:
        parsed = _parse_redis_key(key)
        if parsed:
            value = metrics.redis.get(key)
            parsed["value"] = int(value) if value else 0
            results.append(parsed)
    return results


def _get_all_gauges_by_pattern(pattern: str) -> List[Dict[str, Any]]:
    """获取匹配模式的所有瞬时值"""
    results = []
    keys = metrics.get_metrics_keys_by_pattern(pattern)
    for key in keys:
        parsed = _parse_redis_key(key)
        if parsed:
            value = metrics.redis.get(key)
            parsed["value"] = float(value) if value else 0
            results.append(parsed)
    return results


# ==================== API 端点 ====================

@router.get("/dashboard")
async def get_dashboard() -> Dict[str, Any]:
    """
    获取仪表板数据
    
    返回所有核心指标的实时状态，用于监控页面展示。
    """
    try:
        now = datetime.now()
        
        # ========== 1. 爬取统计 ==========
        crawl_stats = {
            "total": 0,
            "success": 0,
            "error": 0,
            "skipped": 0,
            "success_rate": 0,
            "videos_discovered": 0,
            "avg_duration": 0,
            "by_site": [],
            "skip_reasons": []
        }
        
        # 获取所有 crawl.tasks.total 计数器（成功/失败/跳过）
        task_counters = _get_all_counters_by_pattern("metrics:counter:crawl.tasks.total:*")
        # 获取发现的视频
        video_counters = _get_all_counters_by_pattern("metrics:counter:videos.discovered:*")
        # 获取错误统计
        error_counters = _get_all_counters_by_pattern("metrics:counter:crawl.errors.total:*")
        
        # 按站点汇总
        site_stats = {}
        skip_reasons = {}
        
        for counter in task_counters:
            site = counter["tags"].get("site", "unknown")
            status = counter["tags"].get("status", "unknown")
            reason = counter["tags"].get("reason")
            value = counter["value"]
            
            if site not in site_stats:
                site_stats[site] = {"success": 0, "error": 0, "skipped": 0, "videos": 0, "errors": {}, "skip_reasons": {}}
            
            if status == "success":
                site_stats[site]["success"] += value
                crawl_stats["success"] += value
            elif status == "error":
                site_stats[site]["error"] += value
                crawl_stats["error"] += value
            elif status == "skipped":
                site_stats[site]["skipped"] += value
                crawl_stats["skipped"] += value
                # 统计跳过原因
                if reason:
                    if reason not in skip_reasons:
                        skip_reasons[reason] = 0
                    skip_reasons[reason] += value
                    if reason not in site_stats[site]["skip_reasons"]:
                        site_stats[site]["skip_reasons"][reason] = 0
                    site_stats[site]["skip_reasons"][reason] += value
        
        for counter in video_counters:
            site = counter["tags"].get("site", "unknown")
            value = counter["value"]
            if site not in site_stats:
                site_stats[site] = {"success": 0, "error": 0, "skipped": 0, "videos": 0, "errors": {}, "skip_reasons": {}}
            site_stats[site]["videos"] += value
            crawl_stats["videos_discovered"] += value
        
        for counter in error_counters:
            site = counter["tags"].get("site", "unknown")
            error_type = counter["tags"].get("error_type", "unknown")
            value = counter["value"]
            if site not in site_stats:
                site_stats[site] = {"success": 0, "error": 0, "skipped": 0, "videos": 0, "errors": {}, "skip_reasons": {}}
            if error_type not in site_stats[site]["errors"]:
                site_stats[site]["errors"][error_type] = 0
            site_stats[site]["errors"][error_type] += value
        
        # 计算总数和成功率（跳过的不计入成功率计算）
        crawl_stats["total"] = crawl_stats["success"] + crawl_stats["error"] + crawl_stats["skipped"]
        executed = crawl_stats["success"] + crawl_stats["error"]  # 实际执行的任务数
        if executed > 0:
            crawl_stats["success_rate"] = round(crawl_stats["success"] / executed * 100, 1)
        
        # 转换为列表并排序（过滤掉 total=0 的站点，这些是只有残留错误数据的旧记录）
        for site, stats in site_stats.items():
            total = stats["success"] + stats["error"] + stats["skipped"]
            if total == 0:
                continue  # 跳过没有任务记录的站点
            executed = stats["success"] + stats["error"]  # 实际执行的任务数
            success_rate = round(stats["success"] / executed * 100, 1) if executed > 0 else 0
            crawl_stats["by_site"].append({
                "site": site,
                "total": total,
                "success": stats["success"],
                "error": stats["error"],
                "skipped": stats["skipped"],
                "success_rate": success_rate,
                "videos": stats["videos"],
                "errors": stats["errors"],
                "skip_reasons": stats["skip_reasons"]
            })
        
        # 按总数排序
        crawl_stats["by_site"].sort(key=lambda x: x["total"], reverse=True)
        
        # 添加总体跳过原因统计
        for reason, count in sorted(skip_reasons.items(), key=lambda x: x[1], reverse=True):
            crawl_stats["skip_reasons"].append({"reason": reason, "count": count})
        
        # 获取平均耗时（按站点分组）
        duration_keys = metrics.get_metrics_keys_by_pattern("metrics:histogram:crawl.extract.duration:*")
        all_durations = []
        site_durations = {}  # 按站点存储耗时数据
        
        for key in duration_keys:
            # 从 key 中解析站点信息
            site = "unknown"
            try:
                # key 格式: metrics:histogram:crawl.extract.duration:site=xxx
                parts = key.split(":")
                for part in parts:
                    if part.startswith("site="):
                        site = part.split("=")[1]
                        break
            except Exception:
                pass
            
            if site not in site_durations:
                site_durations[site] = []
            
            members = metrics.redis.zrange(key, 0, -1)
            for member in members:
                if isinstance(member, bytes):
                    member = member.decode('utf-8')
                try:
                    _, value_str = member.split(":", 1)
                    duration = float(value_str)
                    all_durations.append(duration)
                    site_durations[site].append(duration)
                except (ValueError, IndexError):
                    continue
        
        # 计算总体性能指标
        if all_durations:
            all_durations.sort()
            crawl_stats["avg_duration"] = round(sum(all_durations) / len(all_durations), 2)
            crawl_stats["min_duration"] = round(all_durations[0], 2)
            crawl_stats["max_duration"] = round(all_durations[-1], 2)
            crawl_stats["p50_duration"] = round(all_durations[len(all_durations) // 2], 2)
            crawl_stats["p95_duration"] = round(all_durations[int(len(all_durations) * 0.95)], 2) if len(all_durations) > 20 else crawl_stats["max_duration"]
        
        # 为每个站点添加性能指标
        for site_data in crawl_stats["by_site"]:
            site_name = site_data["site"]
            durations = site_durations.get(site_name, [])
            if durations:
                durations.sort()
                site_data["avg_duration"] = round(sum(durations) / len(durations), 2)
                site_data["min_duration"] = round(durations[0], 2)
                site_data["max_duration"] = round(durations[-1], 2)
                site_data["p50_duration"] = round(durations[len(durations) // 2], 2)
                site_data["p95_duration"] = round(durations[int(len(durations) * 0.95)], 2) if len(durations) > 20 else site_data["max_duration"]
            else:
                site_data["avg_duration"] = 0
                site_data["min_duration"] = 0
                site_data["max_duration"] = 0
                site_data["p50_duration"] = 0
                site_data["p95_duration"] = 0
        
        # ========== 2. 队列统计（按站点汇总） ==========
        queue_stats = {
            "total_depth": 0,
            "total_messages": 0
        }
        
        # 按站点汇总队列数据
        site_queue_stats = {}  # {site: {depth: 0, messages: 0, queues: []}}
        
        def _parse_site_from_queue(queue_name: str) -> str:
            """从队列名解析站点，格式: queue:{type}:{site}:{mode}"""
            try:
                parts = queue_name.split(":")
                if len(parts) >= 3:
                    return parts[2]  # site 是第三部分
            except Exception:
                pass
            return "unknown"
        
        # 获取队列深度
        queue_gauges = _get_all_gauges_by_pattern("metrics:gauge:queue.depth:*")
        for gauge in queue_gauges:
            queue_name = gauge["tags"].get("queue", "unknown")
            depth = int(gauge["value"])
            site = _parse_site_from_queue(queue_name)
            
            queue_stats["total_depth"] += depth
            
            if site not in site_queue_stats:
                site_queue_stats[site] = {"depth": 0, "messages": 0, "queues": []}
            site_queue_stats[site]["depth"] += depth
            site_queue_stats[site]["queues"].append({"name": queue_name, "depth": depth})
        
        # 获取队列消息统计
        queue_msg_counters = _get_all_counters_by_pattern("metrics:counter:queue.messages.total:*")
        for counter in queue_msg_counters:
            queue_name = counter["tags"].get("queue", "unknown")
            value = counter["value"]
            site = _parse_site_from_queue(queue_name)
            
            queue_stats["total_messages"] += value
            
            if site not in site_queue_stats:
                site_queue_stats[site] = {"depth": 0, "messages": 0, "queues": []}
            site_queue_stats[site]["messages"] += value
        
        # 将队列数据添加到爬取站点统计中
        for site_data in crawl_stats["by_site"]:
            site_name = site_data["site"]
            # 需要根据域名找到对应的站点标识
            from queues.queue_config import get_queue_config
            config = get_queue_config()
            site_key = config.get_site_by_domain(site_name)
            
            if site_key and site_key in site_queue_stats:
                site_data["queue_depth"] = site_queue_stats[site_key]["depth"]
                site_data["queue_messages"] = site_queue_stats[site_key]["messages"]
            else:
                site_data["queue_depth"] = 0
                site_data["queue_messages"] = 0
        
        # ========== 3. 订阅更新统计 ==========
        subscription_stats = {
            "total": 0,
            "success": 0,
            "error": 0,
            "skipped": 0,
            "success_rate": 0,
            "videos_found": 0,
            "videos_enqueued": 0,
            "by_site": [],
            "skip_reasons": []
        }
        
        # 获取订阅更新计数器
        sub_counters = _get_all_counters_by_pattern("metrics:counter:subscription.update.total:*")
        sub_videos_found = _get_all_counters_by_pattern("metrics:counter:subscription.videos.found:*")
        sub_videos_enqueued = _get_all_counters_by_pattern("metrics:counter:subscription.videos.enqueued:*")
        
        sub_site_stats = {}
        skip_reasons = {}
        
        for counter in sub_counters:
            site = counter["tags"].get("site", "unknown")
            status = counter["tags"].get("status", "unknown")
            reason = counter["tags"].get("reason")
            value = counter["value"]
            
            if site not in sub_site_stats:
                sub_site_stats[site] = {"success": 0, "error": 0, "skipped": 0, "videos_found": 0, "videos_enqueued": 0}
            
            if status == "success":
                sub_site_stats[site]["success"] += value
                subscription_stats["success"] += value
            elif status == "error":
                sub_site_stats[site]["error"] += value
                subscription_stats["error"] += value
            elif status == "skipped":
                sub_site_stats[site]["skipped"] += value
                subscription_stats["skipped"] += value
                if reason:
                    if reason not in skip_reasons:
                        skip_reasons[reason] = 0
                    skip_reasons[reason] += value
        
        # 统计发现和入队的视频数（按站点）
        for counter in sub_videos_found:
            site = counter["tags"].get("site", "unknown")
            value = counter["value"]
            subscription_stats["videos_found"] += value
            if site not in sub_site_stats:
                sub_site_stats[site] = {"success": 0, "error": 0, "skipped": 0, "videos_found": 0, "videos_enqueued": 0}
            sub_site_stats[site]["videos_found"] += value
        
        for counter in sub_videos_enqueued:
            site = counter["tags"].get("site", "unknown")
            value = counter["value"]
            subscription_stats["videos_enqueued"] += value
            if site not in sub_site_stats:
                sub_site_stats[site] = {"success": 0, "error": 0, "skipped": 0, "videos_found": 0, "videos_enqueued": 0}
            sub_site_stats[site]["videos_enqueued"] += value
        
        subscription_stats["total"] = subscription_stats["success"] + subscription_stats["error"] + subscription_stats["skipped"]
        sub_executed = subscription_stats["success"] + subscription_stats["error"]  # 实际执行的任务数
        if sub_executed > 0:
            subscription_stats["success_rate"] = round(subscription_stats["success"] / sub_executed * 100, 1)
        
        # 转换为列表
        for site, stats in sub_site_stats.items():
            total = stats["success"] + stats["error"] + stats["skipped"]
            executed = stats["success"] + stats["error"]  # 实际执行的任务数
            success_rate = round(stats["success"] / executed * 100, 1) if executed > 0 else 0
            subscription_stats["by_site"].append({
                "site": site,
                "total": total,
                "success": stats["success"],
                "error": stats["error"],
                "skipped": stats["skipped"],
                "success_rate": success_rate,
                "videos_found": stats["videos_found"],
                "videos_enqueued": stats["videos_enqueued"]
            })
        
        subscription_stats["by_site"].sort(key=lambda x: x["total"], reverse=True)
        
        for reason, count in sorted(skip_reasons.items(), key=lambda x: x[1], reverse=True):
            subscription_stats["skip_reasons"].append({"reason": reason, "count": count})
        
        # ========== 4. 错误统计 ==========
        error_stats = {
            "total": 0,
            "by_type": [],
            "by_site": []
        }
        
        error_by_type = {}
        error_by_site = {}
        
        for counter in error_counters:
            site = counter["tags"].get("site", "unknown")
            error_type = counter["tags"].get("error_type", "unknown")
            value = counter["value"]
            
            error_stats["total"] += value
            
            if error_type not in error_by_type:
                error_by_type[error_type] = 0
            error_by_type[error_type] += value
            
            if site not in error_by_site:
                error_by_site[site] = 0
            error_by_site[site] += value
        
        for error_type, count in sorted(error_by_type.items(), key=lambda x: x[1], reverse=True):
            error_stats["by_type"].append({"type": error_type, "count": count})
        
        for site, count in sorted(error_by_site.items(), key=lambda x: x[1], reverse=True):
            error_stats["by_site"].append({"site": site, "count": count})
        
        # ========== 5. 计算健康分数 ==========
        health_score = 100
        health_issues = []
        
        # 成功率检查（最高扣40分）
        if crawl_stats["total"] > 0:
            if crawl_stats["success_rate"] < 50:
                health_score -= 40
                health_issues.append(f"爬取成功率过低: {crawl_stats['success_rate']}%")
            elif crawl_stats["success_rate"] < 80:
                health_score -= 20
                health_issues.append(f"爬取成功率偏低: {crawl_stats['success_rate']}%")
        
        # 队列积压检查（最高扣30分）
        if queue_stats["total_depth"] > 1000:
            health_score -= 30
            health_issues.append(f"队列积压严重: {queue_stats['total_depth']}")
        elif queue_stats["total_depth"] > 500:
            health_score -= 15
            health_issues.append(f"队列积压较多: {queue_stats['total_depth']}")
        
        # 错误率检查（最高扣30分）
        if crawl_stats["total"] > 0:
            error_rate = crawl_stats["error"] / crawl_stats["total"] * 100
            if error_rate > 20:
                health_score -= 30
                health_issues.append(f"错误率过高: {round(error_rate, 1)}%")
            elif error_rate > 10:
                health_score -= 15
                health_issues.append(f"错误率偏高: {round(error_rate, 1)}%")
        
        health_status = "healthy" if health_score >= 80 else "degraded" if health_score >= 50 else "critical"
        
        # 获取最近的错误详情
        recent_errors = metrics.get_recent_errors(limit=20)
        
        return {
            "timestamp": now.isoformat(),
            "health": {
                "score": max(0, health_score),
                "status": health_status,
                "issues": health_issues
            },
            "crawl": crawl_stats,
            "subscriptions": subscription_stats,
            "queues": queue_stats,
            "errors": error_stats,
            "recent_errors": recent_errors
        }
        
    except Exception as e:
        logger.error(f"Failed to get dashboard data: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/raw")
async def get_raw_metrics() -> Dict[str, Any]:
    """
    获取原始指标数据（调试用）
    
    返回 Redis 中所有指标的原始数据。
    """
    try:
        result = {
            "counters": [],
            "gauges": [],
            "histograms": []
        }
        
        # 获取所有计数器
        counter_keys = metrics.get_metrics_keys_by_pattern("metrics:counter:*")
        for key in counter_keys:
            parsed = _parse_redis_key(key)
            if parsed:
                value = metrics.redis.get(key)
                result["counters"].append({
                    "key": key if isinstance(key, str) else key.decode('utf-8'),
                    "name": parsed["name"],
                    "tags": parsed["tags"],
                    "value": int(value) if value else 0
                })
        
        # 获取所有瞬时值
        gauge_keys = metrics.get_metrics_keys_by_pattern("metrics:gauge:*")
        for key in gauge_keys:
            parsed = _parse_redis_key(key)
            if parsed:
                value = metrics.redis.get(key)
                result["gauges"].append({
                    "key": key if isinstance(key, str) else key.decode('utf-8'),
                    "name": parsed["name"],
                    "tags": parsed["tags"],
                    "value": float(value) if value else 0
                })
        
        # 获取所有直方图
        histogram_keys = metrics.get_metrics_keys_by_pattern("metrics:histogram:*")
        for key in histogram_keys:
            parsed = _parse_redis_key(key)
            if parsed:
                members = metrics.redis.zrange(key, 0, -1)
                values = []
                for member in members:
                    if isinstance(member, bytes):
                        member = member.decode('utf-8')
                    try:
                        _, value_str = member.split(":", 1)
                        values.append(float(value_str))
                    except:
                        continue
                result["histograms"].append({
                    "key": key if isinstance(key, str) else key.decode('utf-8'),
                    "name": parsed["name"],
                    "tags": parsed["tags"],
                    "count": len(values),
                    "values": values[:100] if len(values) > 100 else values  # 限制返回数量
                })
        
        return result
        
    except Exception as e:
        logger.error(f"Failed to get raw metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/collect")
async def trigger_metrics_collection() -> Dict[str, Any]:
    """
    手动触发指标收集
    
    从 Redis 收集指标快照并持久化到数据库。
    """
    try:
        count = metrics_service.collect_and_persist()
        return {
            "success": True,
            "collected": count,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Failed to trigger metrics collection: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/cleanup")
async def cleanup_old_metrics(
    days: int = Query(30, ge=1, le=365, description="保留天数")
) -> Dict[str, Any]:
    """
    清理过期的指标数据
    """
    try:
        deleted = metrics_service.cleanup_old_metrics(days)
        return {
            "success": True,
            "deleted": deleted,
            "retention_days": days,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Failed to cleanup old metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))
