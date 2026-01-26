import discord
from discord.ext import commands
from discord.ui import Select, View, Button
from aiohttp import web
import google.generativeai as genai
import asyncio
import os
import urllib.parse

# --- 地圖專用資料結構 ---
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
            emoji = "🍴" if "食" in place.category else "🎉"
            options.append(discord.SelectOption(
                label=place.name[:25], 
                description=place.category, 
                emoji=emoji, 
                value=str(index)
            ))
        super().__init__(placeholder="📍 點擊選擇地點查看詳情...", min_values=1, max_values=1, options=options)
        self.places = places

    async def callback(self, interaction: discord.Interaction):
        place = self.places[int(self.values[0])]
        # 製作 Google Maps 搜尋連結
        search_query = urllib.parse.quote(place.name)
        map_url = f"https://www.google.com/maps/search/?api=1&query={search_query}"
        
        embed = discord.Embed(title=f"📍 {place.name}", description=place.description, color=discord.Color.blue())
        embed.add_field(name="類別", value=place.category)
        embed.add_field(name="標籤", value=place.tags)
        embed.set_footer(text="Gemini 推薦")
        
        view = View()
        view.add_item(Button(label="🚀 Google Maps 導航", style=discord.ButtonStyle.link, url=map_url))
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

class MapServer(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        api_key = os.getenv("GEMINI_API_KEY")
        if api_key: genai.configure(api_key=api_key)

    # 當這個模組載入時，自動去掛載到 Web Server
    async def cog_load(self):
        web_cog = self.bot.get_cog('WebServer')
        if web_cog:
            web_cog.add_route('POST', '/recommend', self.handle_recommend)
            print("✅ [地圖] /recommend 路徑已掛載 (Active Mount)")
        else:
            print("❌ [地圖] 無法掛載！找不到 WebServer") 
        web_cog = self.bot.get_cog('WebServer')
        if web_cog:
            # 🔌 把自己的 handle_recommend 插到總機上
            web_cog.add_route('POST', '/recommend', self.handle_recommend)
            print("✅ [地圖] /recommend 路徑已掛載")
        else:
            print("❌ [地圖] 找不到 WebServer，無法掛載 API")

    async def handle_recommend(self, request):
        try:
            data = await request.json()
            lat, lon = data.get('lat'), data.get('lon')
            if not lat: return web.Response(text="No GPS Data", status=400)

            # 👇 修改這裡：從環境變數讀取 Map 專用頻道 ID
            channel_id_str = os.getenv("MAP_CHANNEL_ID")
            if not channel_id_str:
                print("⚠️ 錯誤：Zeabur 環境變數未設定 MAP_CHANNEL_ID")
                return web.Response(text="Server Config Error: MAP_CHANNEL_ID not set", status=500)

            channel = self.bot.get_channel(int(channel_id_str))
            if not channel: return web.Response(text="Channel Not Found", status=404)

            # 先發送「思考中」訊息
            msg = await channel.send(f"🛰️ 收到座標 ({lat}, {lon})，正在分析附近熱點...")
            
            # 呼叫 Gemini AI
            prompt = f"使用者位於座標 {lat},{lon}。請推薦附近 5 個地點(美食/景點)。格式：名稱|介紹|類別|#標籤"
            model = genai.GenerativeModel('models/gemini-2.5-flash')
            response = await asyncio.to_thread(model.generate_content, prompt)
            
            # 解析 AI 回傳的資料
            places = []
            if response.text:
                for line in response.text.strip().split('\n'):
                    parts = line.split('|')
                    if len(parts) >= 4:
                        places.append(LocationData(parts[0], parts[1], parts[2], parts[3]))

            if places:
                view = View()
                view.add_item(PlaceSelect(places))
                await msg.edit(content=f"📍 座標 ({lat:.4f}, {lon:.4f}) 推薦清單：", view=view)
                return web.Response(text="OK")
            
            await msg.edit(content="😵 這一帶好像很荒涼，AI 找不到推薦的地點。")
            return web.Response(text="No Data Found")

        except Exception as e:
            print(f"Map Error: {e}")
            return web.Response(text=str(e), status=500)

async def setup(bot):
    await bot.add_cog(MapServer(bot))