import discord
from discord.ext import commands
import re
import os
from dotenv import load_dotenv
from flask import Flask
import threading
import asyncio
import time
import logging
exports = ['on_message']

load_dotenv()

# ログ設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TOKEN = os.environ.get('DISCORD_TOKEN')
PORT = int(os.environ.get('PORT', 5000))

# Flask app for keeping the server alive
app = Flask(__name__)

@app.route('/')
def health_check():
    return {'status': 'ok'}, 200
# Intentsの設定
intents = discord.Intents.default()
intents.message_content = True  # Message Content Intent を明示
intents.guilds = True
intents.messages = True
temp = ""

bot = commands.Bot(command_prefix="!", intents=intents)

# 対象カテゴリー名
LINK_CATEGORIES = ["リンクメモ"]

# URL判定用正規表現
URL_REGEX = re.compile(r"https?://[^\s]+")

@bot.event
async def on_ready():
    print(f'Botがログインしました: {bot.user}')

@bot.command()
async def text(ctx, amount: int):
    if amount >= 1:
        deleted_messages = await ctx.channel.purge(limit=amount + 1)
        await ctx.send(f'メッセージを{len(deleted_messages) - 1}個削除しました。', delete_after=5)
    else:
        await ctx.send("1以上の数字を入力してください。", delete_after=5)

@bot.event
async def on_message(message):
    global temp
    if message.author.bot:
        return

    if message.channel.category and message.channel.category.name in LINK_CATEGORIES:
        if not URL_REGEX.search(message.content):
            await message.delete()
        else:
            if temp in message.content:
                await message.delete()
            else:
                temp = message.content
    await bot.process_commands(message)


def run_flask():
    """Run Flask server in a separate thread"""
    app.run(host='0.0.0.0', port=PORT, debug=False)


def run_bot_with_retry():
    """Run bot with automatic restart on failure"""
    max_retries = 5
    retry_count = 0
    base_wait_time = 5
    
    while retry_count < max_retries:
        try:
            logger.info(f"Botを起動しています... (試行 {retry_count + 1}/{max_retries})")
            
            # Start Flask server in background thread
            flask_thread = threading.Thread(target=run_flask, daemon=True)
            flask_thread.start()
            logger.info("Flaskサーバーを起動しました")
            
            # Bot を実行
            bot.run(TOKEN)
            
        except Exception as e:
            retry_count += 1
            wait_time = base_wait_time * (2 ** (retry_count - 1))
            logger.error(f"Botが落ちました: {e}")
            logger.info(f"{wait_time}秒後に再起動を試みます... (試行 {retry_count}/{max_retries})")
            time.sleep(wait_time)
    
    logger.critical("最大再試行回数に達しました。ボットを停止します。")


# メイン処理
if __name__ == "__main__":
    run_bot_with_retry()


