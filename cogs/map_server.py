import discord
from discord.ext import commands
from discord.ui import Select, View, Button
from aiohttp import web
import google.generativeai as genai
import asyncio
import os
import urllib.parse

class LocationData:
    def __init__(self, name, description, category, tags):
        self.name = name
        self.description = description
        self.category = category
        self.tags = tags

class PlaceSelect(Select):
    def __init__(self, places):
        options = []
        for index, place in enumerate(places):
            options.append(discord.SelectOption(
                label=f"{index+1}. {place.name[:50]}",
                value=str(index),
                emoji="📍"
            ))
        super().__init__(placeholder="🗺️ 點我開啟 Google Maps 導航...", options=options)
        self.places = places

    async def callback(self, interaction: discord.Interaction):
        place = self.places[int(self.values[0])]
        
        # 使用標準 Google Maps 搜尋連結參數
        search_query = urllib.parse.quote(place.name)
        # api=1 確保喚起 App，query 放地點名稱
        map_url = f"https://www.google.com/maps/search/?api=1&query={search_query}"
        
        view = View()
        view.add_item(Button(label=f"開啟 {place.name} 導航", style=discord.ButtonStyle.link, url=map_url))
        await interaction.response.send_message(f"已經為您準備好 **{place.name}** 的導航連結：", view=view, ephemeral=True)

class MapServer(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        api_key = os.getenv("GEMINI_API_KEY")
        if api_key: genai.configure(api_key=api_key)

    async def cog_load(self):
        web_cog = self.bot.get_cog('WebServer')
        if web_cog:
            web_cog.add_route('POST', '/recommend', self.handle_recommend)
            print("✅ [地圖] /recommend 介面優化版已掛載")

    async def handle_recommend(self, request):
        try:
            data = await request.json()
            lat, lon = float(data.get('lat')), float(data.get('lon'))
            channel = self.bot.get_channel(int(os.getenv("MAP_CHANNEL_ID")))
            
            # 1. 發送讀取中訊息
            msg = await channel.send(f"正在搜尋附近的景點...")

            # 2. 呼叫 Gemini (使用最穩定的 flash-latest)
            model = genai.GenerativeModel('models/gemini-flash-latest')
            prompt = (
                f"請根據座標 {lat}, {lon} 判斷所在行政區。"
                f"並推薦 5 個距離此座標 1.5 公里內的「在地美食」或「知名景點」。"
                f"請排除連鎖速食店（如麥當勞、肯德基）。"
                f"請嚴格遵守此格式，每行一個地點：名稱|介紹(30字內)|類別|#標籤"
            )
            
            response = await asyncio.to_thread(model.generate_content, prompt)
            
            # 3. 解析並建立 Embed (讓資訊直接顯示)
            places = []
            embed = discord.Embed(title="推薦清單", color=discord.Color.orange())
            embed.set_footer(text=f"座標: {lat}, {lon} | 由 Gemini 2.0 提供")

            if response.text:
                lines = response.text.strip().split('\n')
                for i, line in enumerate(lines[:5]):
                    parts = line.split('|')
                    if len(parts) >= 4:
                        p = LocationData(parts[0], parts[1], parts[2], parts[3])
                        places.append(p)
                        # 將詳情直接寫入 Embed Field，不用點開就看得到！
                        embed.add_field(
                            name=f"{i+1}. {p.name} ({p.category})",
                            value=f"{p.description}\n`{p.tags}`",
                            inline=False
                        )

            if places:
                view = View()
                view.add_item(PlaceSelect(places))
                await msg.edit(content="✨ 幫您找到了以下熱點：", embed=embed, view=view)
            else:
                await msg.edit(content="❌ 暫時找不到附近推薦，請稍後再試。")
                
            return web.Response(text="OK")
        except Exception as e:
            print(f"Map Error: {e}")
            return web.Response(text=str(e), status=500)

async def setup(bot):
    await bot.add_cog(MapServer(bot))