#!/bin/bash

# 启动主应用（包含数据库迁移）
python main.py &
MAIN_PID=$!

# 等待几秒确保数据库迁移完成
sleep 5

# 启动 worker
python worker.py &
WORKER_PID=$!

# 监控进程
while true; do
    # 检查主应用是否还在运行
    if ! kill -0 $MAIN_PID 2>/dev/null; then
        echo "Main application crashed, shutting down..."
        kill $WORKER_PID 2>/dev/null
        exit 1
    fi
    
    # 检查 worker 是否还在运行
    if ! kill -0 $WORKER_PID 2>/dev/null; then
        echo "Worker crashed, shutting down..."
        kill $MAIN_PID 2>/dev/null
        exit 1
    fi
    
    sleep 5
done