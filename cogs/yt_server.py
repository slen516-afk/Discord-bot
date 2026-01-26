import discord
from discord.ext import commands
from aiohttp import web
import asyncio
import os

class YTServer(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # 記憶區：用來記錄上一則訊息，做覆蓋用
        self.last_msg_id = None
        self.last_video_url = None

    # 當 Bot 準備好時，自動去跟 WebServer (總機) 報到
    @commands.Cog.listener()
    async def on_ready(self):
        # 等個 1 秒確保總機已經啟動
        await asyncio.sleep(1)
        web_cog = self.bot.get_cog('WebServer')
        
        if web_cog:
            # 🔌 把自己的 handle_pause 插到總機上
            web_cog.add_route('POST', '/pause', self.handle_pause)
            print("✅ [YT] /pause 路徑已掛載")
        else:
            print("❌ [YT] 嚴重錯誤：找不到 WebServer Cog，無法掛載 API！")

    # 工具函式：把 "1:30" 轉成 90 秒
    def parse_time_to_seconds(self, time_str):
        try:
            time_str = time_str.replace('.', ':').replace('：', ':')
            parts = time_str.split(':')
            if len(parts) == 3: # H:M:S
                return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
            elif len(parts) == 2: # M:S
                return int(parts[0]) * 60 + int(parts[1])
            elif len(parts) == 1: # S
                return int(parts[0])
        except:
            return 0
        return 0

    # 核心邏輯：處理 YouTube 請求
    async def handle_pause(self, request):
        try:
            data = await request.json()
            title = data.get('title', '無標題')
            raw_url = data.get('url', '')
            timestamp = data.get('time', '0:00')

            # 1. 讀取環境變數中的 YT 專用頻道 ID
            channel_id_str = os.getenv("YT_CHANNEL_ID")
            if not channel_id_str:
                print("⚠️ 錯誤：Zeabur 環境變數未設定 YT_CHANNEL_ID")
                return web.Response(text="Server Config Error: YT_CHANNEL_ID not set", status=500)
            
            channel = self.bot.get_channel(int(channel_id_str))
            if not channel:
                return web.Response(text="Channel Not Found", status=404)

            # 2. 處理網址與時間跳轉
            final_url = raw_url
            if timestamp and timestamp != '0:00':
                seconds = self.parse_time_to_seconds(timestamp)
                if seconds > 0:
                    # 智慧判斷：原本有問號用 &，沒問號用 ?
                    separator = '&' if '?' in raw_url else '?'
                    final_url = f"{raw_url}{separator}t={seconds}s"

            # 3. 建立 Embed
            embed = discord.Embed(
                title="▶️ 正在觀看影片",
                description=f"[{title}]({final_url})", 
                color=discord.Color.green()
            )
            embed.add_field(name="目前時間點", value=f"⏱️ **{timestamp}**", inline=True)
            
            if title == "iOS 分享":
                embed.set_footer(text="來自 iPhone • 點擊標題跳轉")
            else:
                embed.set_footer(text="來自 Chrome 擴充功能 • 點擊標題跳轉")

            # 4. 判斷是否覆蓋舊訊息 (同一部影片就編輯，不同部就發新的)
            is_same_video = False
            if self.last_video_url:
                # 簡單比對網址 (忽略時間參數)
                clean_new = raw_url.split('&')[0].split('?t=')[0]
                clean_old = self.last_video_url.split('&')[0].split('?t=')[0]
                if clean_new == clean_old:
                    is_same_video = True

            if self.last_msg_id and is_same_video:
                try:
                    msg = await channel.fetch_message(self.last_msg_id)
                    await msg.edit(embed=embed)
                    self.last_video_url = raw_url # 更新連結 (因為時間變了)
                    return web.Response(text="Message Updated")
                except discord.NotFound:
                    pass # 舊訊息被刪了，就往下走發新的

            # 發送新訊息
            msg = await channel.send(embed=embed)
            self.last_msg_id = msg.id
            self.last_video_url = raw_url
            
            return web.Response(text="New Message Sent")

        except Exception as e:
            print(f"❌ YT API Error: {e}")
            # CORS 已經由 web.py 處理，這裡只要回傳錯誤訊息即可
            return web.Response(text=f"Error: {str(e)}", status=500)

async def setup(bot):
    await bot.add_cog(YTServer(bot))