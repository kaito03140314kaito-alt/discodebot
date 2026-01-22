import discord
from discord.ext import tasks, commands
import feedparser
import os
from keep_alive import keep_alive
import glob

# 環境変数から設定を読み込み
TOKEN = os.environ['DISCORD_TOKEN']
CHANNEL_ID = int(os.environ['CHANNEL_ID'])
RSS_URL = os.environ['RSS_URL']

# Intentsの設定
intents = discord.Intents.default()
intents.message_content = True # コマンドを受け取るために必要

# ClientからBotに変更してコマンド機能を利用しやすくする
bot = commands.Bot(command_prefix='!', intents=intents)

last_link = None

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user}')
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
    channel = bot.get_channel(CHANNEL_ID)
    
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
            if channel:
                await channel.send(text)
            
            # 最新URLを更新
            last_link = current_link

    except Exception as e:
        print(f"エラー発生: {e}")

# --- ボイスチャット関連機能 ---

@bot.command()
async def join(ctx):
    """ボイスチャットに参加させます"""
    if ctx.author.voice is None:
        await ctx.send("まずはあなたがボイスチャンネルに入ってください。")
        return
    
    channel = ctx.author.voice.channel
    if ctx.voice_client is not None:
        await ctx.voice_client.move_to(channel)
    else:
        await channel.connect()
    await ctx.send("接続しました！")

@bot.command()
async def play(ctx):
    """同じフォルダにある音声ファイルを再生します"""
    if ctx.voice_client is None:
        await ctx.send("まだボイスチャンネルに入っていません。`!join`で呼んでください。")
        return

    # カレントディレクトリのmp3やwavを探す
    files = glob.glob("*.mp3") + glob.glob("*.wav") + glob.glob("*.m4a")
    
    if not files:
        await ctx.send("再生できる音声ファイルが見つかりませんでした。(mp3, wav, m4a)")
        return
    
    # 最初に見つかったファイルを再生
    source_file = files[0]
    
    # 再生中なら止める
    if ctx.voice_client.is_playing():
        ctx.voice_client.stop()

    ctx.voice_client.play(discord.FFmpegPCMAudio(source_file))
    await ctx.send(f"再生しています: `{source_file}`")

@bot.command()
async def stop(ctx):
    """再生を停止して切断します"""
    if ctx.voice_client:
        await ctx.voice_client.disconnect()
        await ctx.send("切断しました。")

keep_alive()
bot.run(TOKEN)
