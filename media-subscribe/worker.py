# start_workers.py
import subprocess
import sys
import platform
from typing import List

def get_python_prefix() -> List[str]:
    """根据平台返回正确的Python命令前缀"""
    if platform.system() == "Windows":
        return ["pipenv", "run"]
    return ["pipenv", "run"]

def start_workers():
    # 定义队列列表
    queues = [
        "video_download_queue",
        "video_subscribe_queue",
        "channel_video_extract_download_queue",
        "extract_bilibili",
        "extract_pornhub",
        "extract_youtube",
        "extract_javdb",
    ]
    
    processes = []
    python_prefix = get_python_prefix()
    
    try:
        # 启动每个队列的worker
        for queue in queues:
            cmd = [
                *python_prefix,
                "dramatiq",
                "consumer",
                "-Q",
                queue,
                "--processes",
                "1",
                "--threads",
                "1"
            ]
            
            # 在Windows上，使用CREATE_NEW_CONSOLE来创建新的控制台窗口
            if platform.system() == "Windows":
                process = subprocess.Popen(
                    cmd,
                    creationflags=subprocess.CREATE_NEW_CONSOLE
                )
            else:
                process = subprocess.Popen(cmd)
            
            processes.append(process)
            print(f"Started worker for queue: {queue}")
        
        # 等待所有进程完成
        for process in processes:
            process.wait()
            
    except KeyboardInterrupt:
        print("\nStopping all workers...")
        # 终止所有进程
        for process in processes:
            if platform.system() == "Windows":
                process.kill()
            else:
                process.terminate()
        
        sys.exit(0)

if __name__ == "__main__":
    print("Starting workers...")
    start_workers()