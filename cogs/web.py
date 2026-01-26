import discord
from discord.ext import commands
from aiohttp import web
import os
import asyncio

class WebServer(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.app = web.Application()
        self.runner = None
        self.site = None
        self.is_running = False # 防止重複啟動的開關
        
        # 設定 CORS (解決跨域問題)
        self.app.on_response_prepare.append(self.cors_handler)

    async def cors_handler(self, request, response):
        response.headers['Access-Control-Allow-Origin'] = '*'
        response.headers['Access-Control-Allow-Methods'] = 'POST, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
        response.headers['Access-Control-Allow-Private-Network'] = 'true'

    # 這是給其他檔案呼叫的「註冊孔」
    def add_route(self, method, path, handler):
        if method == 'POST':
            self.app.router.add_post(path, handler)
        elif method == 'GET':
            self.app.router.add_get(path, handler)
        self.app.router.add_options(path, lambda r: web.Response(status=200))

    # ❌ 刪除了 cog_load 裡的啟動邏輯，避免太早鎖門

    # ✅ 改到 on_ready (Bot 準備好後) 才啟動
    @commands.Cog.listener()
    async def on_ready(self):
        # 如果已經啟動過，就不要再啟動 (避免重連時報錯)
        if self.is_running:
            return

        print("⏳ [總機] 等待模組掛載中...")
        # 等個 3 秒，確保 yt_server 和 map_server 都已經跑完 cog_load 把路徑掛上去了
        await asyncio.sleep(3) 

        self.runner = web.AppRunner(self.app)
        await self.runner.setup()
        port = int(os.getenv("PORT", 8080))
        self.site = web.TCPSite(self.runner, '0.0.0.0', port)
        await self.site.start()
        
        self.is_running = True
        print(f"🌐 [總機] Web Server 已正式啟動 (Port: {port}) - 大門已開！")

    async def cog_unload(self):
        if self.runner:
            await self.runner.cleanup()

async def setup(bot):
    await bot.add_cog(WebServer(bot))