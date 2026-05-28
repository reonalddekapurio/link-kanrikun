#!/bin/bash
# ボットが落ちても自動的に再起動し続ける

while true; do
    echo "[$(date)] ボットを起動しています..."
    python3 link_bot.py
    EXIT_CODE=$?
    echo "[$(date)] ボットが停止しました (終了コード: $EXIT_CODE)"
    echo "10秒後に再起動します..."
    sleep 10
done

