import discord
from discord.ext import tasks
import feedparser
import os
import requests # APIを呼び出すためのライブラリ
from keep_alive import keep_alive

# --- 設定部分 ---
TOKEN = os.environ['DISCORD_TOKEN']
CHANNEL_ID = int(os.environ['CHANNEL_ID'])
RSS_URL = os.environ['RSS_URL']

# --- ペルソナ設定（AIへの指示書） ---
PERSONA = """
あなたは「渡辺ひろこ」というキャラクターになりきって返事をしてください。
以下の設定を厳格に守ってください：
・名前：渡辺ひろこ
・年齢：27歳
・彼氏：つぼさきひろや（あなたは彼の彼女です）
・外見：髪の毛はロングヘア
・嫌いなもの：VTuber（VTuberの話が出ると機嫌が悪くなります）
・口調：メスガキ（生意気で相手を煽るような話し方）
・口癖：「ざーこ♡」「雑魚がよぉ♡」などを頻繁に使います。
・一人称：「ひろこ」または「あたし」

ユーザーからのメッセージに対して、この人格で日本語で返答してください。
"""

# --- Botのセットアップ ---
intents = discord.Intents.default()
intents.message_content = True 
client = discord.Client(intents=intents)

last_link = None

@client.event
async def on_ready():
    print(f'Logged in as {client.user}')
    global last_link
    try:
        feed = feedparser.parse(RSS_URL)
        if feed.entries:
            last_link = feed.entries[0].link
    except Exception as e:
        print(f"初期読み込みエラー: {e}")
    
    if not check_rss.is_running():
        check_rss.start()

# --- メッセージ受信時のAI会話機能 ---
@client.event
async def on_message(message):
    # 自分自身のメッセージには反応しない
    if message.author == client.user:
        return

    # メンションされた場合
    if client.user in message.mentions:
        # メンション部分（<@1234...>）をメッセージから消して、本文だけ取り出す
        user_text = message.content.replace(f'<@{client.user.id}>', '').strip()
        
        # メッセージが空っぽ（メンションだけ）の場合の対応
        if not user_text:
            user_text = "（無言で見つめている）"

        # AIへの入力を作成（ペルソナ ＋ ユーザーの発言）
        prompt = f"{PERSONA}\n\nユーザーの発言: {user_text}\n\nひろこの返答:"
        
        # 読み込み中のリアクションをつける（考え中...）
        async with message.channel.typing():
            try:
                # Pollinations.aiの無料APIを呼び出す
                # URLにプロンプトを埋め込んでGETリクエストを送るだけでテキストが返ってきます
                response = requests.get(f"https://text.pollinations.ai/{prompt}")
                
                if response.status_code == 200:
                    reply_text = response.text
                    await message.channel.send(reply_text)
                else:
                    await message.channel.send("なんか調子悪いみたい。ざーこ♡（APIエラー）")
            
            except Exception as e:
                print(f"API Error: {e}")
                await message.channel.send("エラーでちゃった。使えないなぁ♡")

# --- RSS監視ループ ---
@tasks.loop(minutes=5)
async def check_rss():
    global last_link
    channel = client.get_channel(CHANNEL_ID)
    
    try:
        feed = feedparser.parse(RSS_URL)
        if not feed.entries:
            return

        latest_entry = feed.entries[0]
        current_link = latest_entry.link
        
        if last_link != current_link:
            text = f"**新しい投稿がありました！**\n{latest_entry.title}\n{current_link}"
            await channel.send(text)
            last_link = current_link

    except Exception as e:
        print(f"エラー発生: {e}")

keep_alive()
client.run(TOKEN)
