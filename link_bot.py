import discord
from discord.ext import commands
import re
import os
from dotenv import load_dotenv
exports = ['on_message']

load_dotenv()

TOKEN = os.environ.get('DISCORD_TOKEN')
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

@bot.event
async def on_message(message):
    if message.author.bot:
        return

    if message.channel.category and message.channel.category.name in LINK_CATEGORIES:
        if not URL_REGEX.search(message.content):
            await message.delete()
            return

@bot.event
async def on_message(message):
    if message.author.bot:
        return

    if message.channel.category and message.channel.category.name in LINK_CATEGORIES:
        if URL_REGEX.search(message.content):
            if temp != message.content:
                await message.delete()
            temp = message.content
            return
        


    await bot.process_commands(message)
@bot.command()
async def text(ctx,amount:int):
    if amount < 1:
        await ctx.send("1以上の数字を入力してください")
        
        delete = await ctx.channel.purge(limit=amount+1)
        
        await ctx(f'len{delete - 1}個のメッセージを削除しました',delete_after=5)
        
bot.run(TOKEN)


