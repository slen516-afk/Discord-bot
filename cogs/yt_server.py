import discord
from discord.ext import commands
from aiohttp import web
import asyncio
import os

# 設定你想要 Bot 發送訊息的頻道 ID
TARGET_CHANNEL_ID = 1464948032100634750

class YTServer(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.app = web.Application()
        
        self.app.router.add_post('/pause', self.handle_pause)
        self.app.router.add_options('/pause', self.handle_options)
        
        self.runner = None
        self.site = None

        # 🧠【新增記憶區】用來記錄上一次發的訊息
        self.last_msg_id = None    # 存訊息 ID
        self.last_video_url = None # 存影片網址 (用來判斷是不是同一部)

    async def cog_load(self):
        self.runner = web.AppRunner(self.app)
        await self.runner.setup()
        port = int(os.getenv("PORT", 5000))
        self.site = web.TCPSite(self.runner, '0.0.0.0', port)
        await self.site.start()
        print(f"🌐 Bot 內部 Web Server 已啟動，監聽 Port: {port}")

    async def cog_unload(self):
        if self.runner:
            await self.runner.cleanup()

    async def handle_options(self, request):
        return web.Response(status=200, headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "POST, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type",
            "Access-Control-Allow-Private-Network": "true"
        })

    async def handle_pause(self, request):
        cors_headers = {
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Private-Network": "true"
        }

        try:
            data = await request.json()
            title = data.get('title', '無標題')
            url = data.get('url', '') # 這是含時間的完整網址
            timestamp = data.get('time', '0:00')

            # 簡單處理一下 URL，去掉時間參數來比對是否為同一部影片
            # 例如 https://youtu.be/abc?t=10 -> https://youtu.be/abc
            base_url = url.split('?')[0] if '?' in url else url

            channel = self.bot.get_channel(TARGET_CHANNEL_ID)
            if not channel:
                return web.Response(text="Channel Not Found", status=404, headers=cors_headers)

            # 🎨 建立 Embed
            embed = discord.Embed(
                title="▶️ 正在觀看影片", # 標題稍微改一下，比較像狀態
                description=f"[{title}]({url})",
                color=discord.Color.green() # 改成綠色，比較像 Live 狀態
            )
            embed.add_field(name="目前時間點", value=f"⏱️ **{timestamp}**", inline=True)
            embed.set_footer(text="來自 Chrome 擴充功能 • 即時更新中")

            # 🧠【核心邏輯】判斷是要「發送新訊息」還是「修改舊訊息」
            # 條件：如果有上一次的紀錄 AND 是同一部影片 (base_url 相同)
            if self.last_msg_id and self.last_video_url == base_url:
                try:
                    # 嘗試抓取舊訊息
                    msg = await channel.fetch_message(self.last_msg_id)
                    # 修改它 (Edit)
                    await msg.edit(embed=embed)
                    print(f"♻️ 已更新訊息: {title} ({timestamp})")
                    return web.Response(text="Message Updated", headers=cors_headers)
                except discord.NotFound:
                    # 如果舊訊息被手動刪掉了，就沒辦法改，只能往下走去發新的
                    print("⚠️ 舊訊息找不到，準備發送新的")

            # 如果是新影片，或是舊訊息找不到 -> 發送新訊息
            msg = await channel.send(embed=embed)
            
            # 📝 記住這次的資訊
            self.last_msg_id = msg.id
            self.last_video_url = base_url
            
            print(f"✅ 已發送新訊息: {title}")
            return web.Response(text="New Message Sent", headers=cors_headers)

        except Exception as e:
            print(f"❌ API 錯誤: {e}")
            return web.Response(text="Error", status=500, headers=cors_headers)

async def setup(bot):
    await bot.add_cog(YTServer(bot))