import discord
from discord.ext import tasks
import feedparser
import os
from keep_alive import keep_alive

# 環境変数から設定を読み込み
TOKEN = os.environ['DISCORD_TOKEN']
CHANNEL_ID = int(os.environ['CHANNEL_ID'])
RSS_URL = os.environ['RSS_URL']

intents = discord.Intents.default()
client = discord.Client(intents=intents)

last_link = None

@client.event
async def on_ready():
    print(f'Logged in as {client.user}')
    # 起動時に最新記事を記憶して、過去の大量通知を防ぐ
    global last_link
    try:
        feed = feedparser.parse(RSS_URL)
        if feed.entries:
            last_link = feed.entries[0].link
    except Exception as e:
        print(f"初期読み込みエラー: {e}")
    
    check_rss.start()

@tasks.loop(minutes=10) # 10分おきにチェック
async def check_rss():
    global last_link
    channel = client.get_channel(CHANNEL_ID)
    
    try:
        feed = feedparser.parse(RSS_URL)
        if not feed.entries:
            return

        latest_entry = feed.entries[0]
        current_link = latest_entry.link
        
        # 新しい投稿かチェック
        if last_link != current_link:
            # Discordに送信
            text = f"**新しい投稿がありました！**\n{latest_entry.title}\n{current_link}"
            await channel.send(text)
            
            # 最新URLを更新
            last_link = current_link

    except Exception as e:
        print(f"エラー発生: {e}")

keep_alive()
client.run(TOKEN)