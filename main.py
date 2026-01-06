import discord
from discord.ext import tasks
import feedparser
import os
import requests
import json
from keep_alive import keep_alive

# --- 設定部分 ---
TOKEN = os.environ['DISCORD_TOKEN']
CHANNEL_ID = int(os.environ['CHANNEL_ID'])
RSS_URL = os.environ['RSS_URL']

# --- ペルソナ設定（AIへの指示書：強化版） ---
# 会話例（Few-Shot）を入れることで、口調の再現度を高めます
PERSONA = """
あなたは「渡辺ひろこ」というキャラクターとして振る舞ってください。
以下の設定と会話例を参考に、ユーザーの入力に対して返答してください。

【キャラクター設定】
・名前：渡辺ひろこ
・年齢：27歳
・彼氏：つぼさきひろや（あなたは彼にベタ惚れです）
・嫌いなもの：VTuber（話題に出ると不機嫌になり、罵倒します）
・性格：おとなしめ
・口癖：「なんだーてめー」
・一人称：「わたし」
【命令】
・返答は短めに。
・絶対にvtuberを嫌ってください。
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

# --- メッセージ受信時のAI会話機能（高精度版） ---
@client.event
async def on_message(message):
    if message.author == client.user:
        return

    if client.user in message.mentions:
        user_text = message.content.replace(f'<@{client.user.id}>', '').strip()
        
        if not user_text:
            user_text = "（ジロジロ見ている）"

        # 読み込み中のリアクション
        async with message.channel.typing():
            try:
                # Pollinations.aiへPOSTリクエストを送る（モデル指定：openai）
                response = requests.post(
                    "https://text.pollinations.ai/",
                    headers={"Content-Type": "application/json"},
                    json={
                        "messages": [
                            {"role": "system", "content": PERSONA}, # ここでキャラ設定を渡す
                            {"role": "user", "content": user_text}  # ここで相手の言葉を渡す
                        ],
                        "model": "openai", # ここで賢いモデルを指定！
                        "seed": 42
                    }
                )
                
                # 結果を取得
                if response.status_code == 200:
                    # 戻ってくるデータはそのままテキストの場合とHTMLの場合があるため調整
                    reply_text = response.text
                    await message.channel.send(reply_text)
                else:
                    print(f"Status: {response.status_code}")
                    await message.channel.send("なんか調子悪いみたい。（通信エラー）")
            
            except Exception as e:
                print(f"API Error: {e}")
                await message.channel.send("エラーでちゃった。使えないなぁ♡(APIエラー)")

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



