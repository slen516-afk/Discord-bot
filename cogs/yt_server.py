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

        # 記憶區
        self.last_msg_id = None
        self.last_video_url = None

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
    
    # 時間轉換工具 (把 "1:30" 變 90)
    def parse_time_to_seconds(self, time_str):
        try:
            # 處理使用者可能輸入 "1.30" 或 "1:30" 的情況
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

    async def handle_pause(self, request):
        cors_headers = {
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Private-Network": "true"
        }

        try:
            data = await request.json()
            title = data.get('title', '無標題')
            raw_url = data.get('url', '')
            timestamp = data.get('time', '0:00')

            # 🛠️ 修正重點：不再暴力切割網址，改為「疊加參數」
            final_url = raw_url
            
            # 如果有輸入時間，就進行處理
            if timestamp and timestamp != '0:00':
                seconds = self.parse_time_to_seconds(timestamp)
                if seconds > 0:
                    # 判斷網址原本有沒有問號 (?)
                    # 如果有 (例如 watch?v=ID)，我們用 '&' 接在後面
                    # 如果沒有 (例如 youtu.be/ID)，我們用 '?' 接在後面
                    separator = '&' if '?' in raw_url else '?'
                    final_url = f"{raw_url}{separator}t={seconds}s"

            channel = self.bot.get_channel(TARGET_CHANNEL_ID)
            if not channel:
                return web.Response(text="Channel Not Found", status=404, headers=cors_headers)

            # 建立 Embed
            embed = discord.Embed(
                title="▶️ 正在觀看影片",
                description=f"[{title}]({final_url})", # 使用正確帶時間的網址
                color=discord.Color.green()
            )
            embed.add_field(name="目前時間點", value=f"⏱️ **{timestamp}**", inline=True)
            
            if title == "iOS 分享": # 識別是手機來的
                embed.set_footer(text="來自 iPhone • 點擊標題跳轉")
            else:
                embed.set_footer(text="來自 Chrome 擴充功能 • 點擊標題跳轉")

            # 判斷是否為同一部影片 (這次用簡單的字串包含來判斷，避免切壞網址)
            # 如果新的網址裡包含舊的網址 (或是反過來)，就當作同一部
            is_same_video = False
            if self.last_video_url:
                # 簡單比對：忽略參數後的網址是否相同
                clean_new = raw_url.split('&')[0].split('?t=')[0]
                clean_old = self.last_video_url.split('&')[0].split('?t=')[0]
                if clean_new == clean_old:
                    is_same_video = True

            if self.last_msg_id and is_same_video:
                try:
                    msg = await channel.fetch_message(self.last_msg_id)
                    await msg.edit(embed=embed)
                    # 更新記憶中的 URL (用新的帶時間的)
                    self.last_video_url = raw_url 
                    return web.Response(text="Message Updated", headers=cors_headers)
                except discord.NotFound:
                    pass

            msg = await channel.send(embed=embed)
            self.last_msg_id = msg.id
            self.last_video_url = raw_url # 記住原始網址
            
            return web.Response(text="New Message Sent", headers=cors_headers)

        except Exception as e:
            print(f"❌ API 錯誤: {e}")
            return web.Response(text="Error", status=500, headers=cors_headers)

async def setup(bot):
    await bot.add_cog(YTServer(bot))