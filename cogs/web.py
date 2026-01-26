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
        
        # 設定全域 CORS (所有接進來的路由都自動支援跨域)
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
        # 自動補上 OPTIONS (給瀏覽器檢查用)
        self.app.router.add_options(path, lambda r: web.Response(status=200))

    async def cog_load(self):
        self.runner = web.AppRunner(self.app)
        await self.runner.setup()
        port = int(os.getenv("PORT", 8080)) # Zeabur 預設
        self.site = web.TCPSite(self.runner, '0.0.0.0', port)
        await self.site.start()
        print(f"🌐 [總機] Web Server 已啟動，監聽 Port: {port}")

    async def cog_unload(self):
        if self.runner:
            await self.runner.cleanup()

async def setup(bot):
    await bot.add_cog(WebServer(bot))