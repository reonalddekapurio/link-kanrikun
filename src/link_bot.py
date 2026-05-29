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
import sys
import signal
import traceback
from urllib.request import urlopen

exports = ['on_message']

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [%(levelname)s] %(message)s'
)
logger = logging.getLogger(__name__)

TOKEN = os.environ.get('DISCORD_TOKEN', '').strip()
PORT = int(os.environ.get('PORT', 5000))
SERVICE_URL = os.environ.get('SERVICE_URL')

logger.info(f"TOKEN exists: {bool(TOKEN)}")
logger.info(f"TOKEN length: {len(TOKEN) if TOKEN else 0}")
logger.info(f"PORT: {PORT}")

if not TOKEN:
    logger.critical("DISCORD_TOKEN が設定されていません")
    sys.exit(1)

app = Flask(__name__)

@app.route('/')
def health_check():
    return {'status': 'ok'}, 200

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.messages = True

temp = ""
retry_count = 0
bot = None

LINK_CATEGORIES = ["リンクメモ"]

URL_REGEX = re.compile(r"https?://[^\s]+")


def create_bot():
    bot = commands.Bot(command_prefix="!", intents=intents)
    
    @bot.event
    async def on_ready():
        logger.info(f'Botがログインしました: {bot.user}')
    
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
    
    @bot.event
    async def on_error(event, *args, **kwargs):
        logger.error(f"イベントエラー ({event}): {sys.exc_info()}")
        logger.error(traceback.format_exc())
    
    return bot


def run_flask():
    try:
        logger.info(f"Flaskサーバーをポート {PORT} で起動しています...")
        logger.info(f"アクセスURL: http://0.0.0.0:{PORT}")
        app.run(host='0.0.0.0', port=PORT, debug=False, use_reloader=False, threaded=True)
    except Exception as e:
        logger.error(f"Flaskサーバーエラー: {e}")
        logger.error(traceback.format_exc())


def keep_alive_ping():
    if not SERVICE_URL:
        logger.info("SERVICE_URLが未設定のためkeep-aliveなし")
        return
    
    logger.info(f"keep-alive設定済み: {SERVICE_URL}")
    
    while True:
        try:
            time.sleep(300)
            urlopen(SERVICE_URL, timeout=5)
            logger.debug("keep-alive ping送信")
        except Exception as e:
            logger.warning(f"keep-alive失敗: {e}")


async def run_bot_with_login_timeout(bot_instance, token, timeout_seconds=60):
    login_task = asyncio.create_task(bot_instance.start(token))
    
    try:
        await asyncio.wait_for(login_task, timeout=timeout_seconds)
    except asyncio.TimeoutError:
        logger.error(f"ログインタイムアウト ({timeout_seconds}秒)")
        await bot_instance.close()
        raise Exception("ログインタイムアウト")
    except Exception as e:
        logger.error(f"ログイン中にエラー: {e}")
        raise


def run_bot_with_retry():
    global retry_count, bot
    
    max_retries = float('inf')
    retry_count = 0
    base_wait_time = 60
    
    while True:
        try:
            logger.info(f"[Bot] ボット起動処理開始 (試行回数: {retry_count})")
            

            flask_thread = threading.Thread(target=run_flask, daemon=True)
            flask_thread.start()
            logger.info("Flaskサーバーが起動しました")
            
            if SERVICE_URL:
                keep_alive_thread = threading.Thread(target=keep_alive_ping, daemon=True)
                keep_alive_thread.start()
            
            bot = create_bot()
            logger.info("ボットインスタンスを作成しました")
            
            logger.info("client.login() 実行中...")
            bot.run(TOKEN)
            
        except KeyboardInterrupt:
            logger.info("キーボード割り込みを受信しました。ボットを停止します。")
            sys.exit(0)
        except Exception as e:
            retry_count += 1

            wait_time = min(600, base_wait_time * (2 ** (retry_count - 1)))
            logger.error(f"[Bot] ボットが落ちました: {e}")
            logger.error(traceback.format_exc())
            logger.info(f"{wait_time}秒後にリトライを試みます... (試行: {retry_count})")
            
            try:
                time.sleep(wait_time)
            except KeyboardInterrupt:
                logger.info("キーボード割り込みを受信しました。ボットを停止します。")
                sys.exit(0)


# 未処理の例外をキャッチ
def handle_unhandled_exception(exc_type, exc_value, exc_traceback):
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return
    
    logger.critical("未処理の例外が発生しました:")
    logger.critical("".join(traceback.format_exception(exc_type, exc_value, exc_traceback)))


sys.excepthook = handle_unhandled_exception


if __name__ == "__main__":
    logger.info("=" * 50)
    logger.info("Discord Bot を起動します")
    logger.info("=" * 50)
    
    try:
        run_bot_with_retry()
    except KeyboardInterrupt:
        logger.info("ボットを停止しました")
        sys.exit(0)
    except Exception as e:
        logger.critical(f"予期しないエラーが発生しました: {e}")
        logger.critical(traceback.format_exc())
        sys.exit(1)


