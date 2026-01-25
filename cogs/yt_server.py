import discord
from discord.ext import commands
from aiohttp import web
import asyncio
import os  # <--- 這個一定要有

# 設定你想要 Bot 發送訊息的頻道 ID
TARGET_CHANNEL_ID = 1464948032100634750

class YTServer(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.app = web.Application()
        
        # 1. 註冊 POST (傳送資料用)
        self.app.router.add_post('/pause', self.handle_pause)
        # 2. 註冊 OPTIONS (瀏覽器安全檢查用 - 重要!)
        self.app.router.add_options('/pause', self.handle_options)
        
        self.runner = None
        self.site = None

    # 👇👇👇 這裡是被修改的地方 👇👇👇
    async def cog_load(self):
        self.runner = web.AppRunner(self.app)
        await self.runner.setup()
        
        # 修改 1: 從環境變數抓 Port (Zeabur 會自動分配，如果沒有就用 5000)
        port = int(os.getenv("PORT", 5000))
        
        # 修改 2: 監聽 0.0.0.0 (這樣外部才連得進來)
        self.site = web.TCPSite(self.runner, '0.0.0.0', port)
        
        await self.site.start()
        print(f"🌐 Bot 內部 Web Server 已啟動，監聽 Port: {port}")
    # 👆👆👆 修改結束 👆👆👆

    async def cog_unload(self):
        if self.runner:
            await self.runner.cleanup()

    # --- 處理瀏覽器的安全檢查 (CORS) ---
    async def handle_options(self, request):
        return web.Response(status=200, headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "POST, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type",
            "Access-Control-Allow-Private-Network": "true"
        })

    async def handle_pause(self, request):
        """處理來自瀏覽器的暫停請求"""
        
        cors_headers = {
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Private-Network": "true"
        }

        try:
            data = await request.json()
            title = data.get('title', '無標題')
            url = data.get('url', '')
            timestamp = data.get('time', '0:00')

            channel = self.bot.get_channel(TARGET_CHANNEL_ID)
            if channel:
                embed = discord.Embed(
                    title="⏸️ 影片暫停紀錄",
                    description=f"[{title}]({url})",
                    color=discord.Color.red()
                )
                embed.add_field(name="時間軸", value=f"`{timestamp}`", inline=True)
                embed.set_footer(text="來自 Chrome 擴充功能")
                
                await channel.send(embed=embed)
                print(f"已傳送: {title} 到 Discord")
                return web.Response(text="Message Sent", headers=cors_headers)
            else:
                print(f"❌ 找不到頻道 ID: {TARGET_CHANNEL_ID}，請檢查 Bot 是否在該伺服器且有權限")
                return web.Response(text="Channel Not Found", status=404, headers=cors_headers)

        except Exception as e:
            print(f"❌ API 錯誤: {e}")
            return web.Response(text="Error", status=500, headers=cors_headers)

async def setup(bot):
    await bot.add_cog(YTServer(bot))