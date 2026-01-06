import discord
from discord.ext import tasks
import feedparser
import os
from keep_alive import keep_alive

# --- 設定部分 ---
TOKEN = os.environ['DISCORD_TOKEN']
CHANNEL_ID = int(os.environ['CHANNEL_ID'])
RSS_URL = os.environ['RSS_URL']

# --- Botのセットアップ ---
intents = discord.Intents.default()
# 【重要】メッセージの中身やメンションを読み取る許可をONにする
intents.message_content = True 
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
    
    # ループが既に回っていなければ開始
    if not check_rss.is_running():
        check_rss.start()

# --- 【追加】メンションされたら返事をする機能 ---
@client.event
async def on_message(message):
    # 自分自身（Bot）のメッセージには反応しない（無限ループ防止）
    if message.author == client.user:
        return

    # メッセージの中に「自分へのメンション」が含まれているかチェック
    if client.user in message.mentions:
        await message.channel.send("私はひろやの彼女ひろこよ")

# --- RSS監視ループ ---
@tasks.loop(minutes=5) # 5分おきにチェック
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
