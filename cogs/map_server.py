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
            emoji = "🍴" if "食" in place.category else "🎉"
            # ✅ 修正點：強制截斷標籤長度，確保在 1-100 字元內
            safe_label = place.name[:80] if place.name else f"地點 {index+1}"
            options.append(discord.SelectOption(
                label=safe_label, 
                description=place.category[:50], 
                emoji=emoji, 
                value=str(index)
            ))
        super().__init__(placeholder="📍 點擊選擇地點查看詳情...", min_values=1, max_values=1, options=options)
        self.places = places

    async def callback(self, interaction: discord.Interaction):
        place = self.places[int(self.values[0])]
        search_query = urllib.parse.quote(place.name)
        map_url = f"https://www.google.com/maps/search/?api=1&query={search_query}"
        
        embed = discord.Embed(title=f"📍 {place.name}", description=place.description, color=discord.Color.blue())
        embed.add_field(name="類別", value=place.category, inline=True)
        embed.add_field(name="標籤", value=place.tags, inline=True)
        embed.set_footer(text="Gemini 推薦")
        
        view = View()
        view.add_item(Button(label="🚀 Google Maps 導航", style=discord.ButtonStyle.link, url=map_url))
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

class MapServer(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        api_key = os.getenv("GEMINI_API_KEY")
        if api_key: genai.configure(api_key=api_key)

    async def cog_load(self):
        web_cog = self.bot.get_cog('WebServer')
        if web_cog:
            web_cog.add_route('POST', '/recommend', self.handle_recommend)
            print("✅ [地圖] /recommend 路徑已掛載 (Active Mount)")

    async def handle_recommend(self, request):
        try:
            data = await request.json()
            try:
                lat = float(data.get('lat'))
                lon = float(data.get('lon'))
            except:
                return web.Response(text="Invalid GPS", status=400)

            channel_id = os.getenv("MAP_CHANNEL_ID")
            channel = self.bot.get_channel(int(channel_id))
            if not channel: return web.Response(text="Channel Not Found", status=404)

            msg = await channel.send(f"🛰️ 收到汐止座標 ({lat}, {lon})，正在搜尋在地美食...")

            # ✅ 修正點：改用你清單中最穩定的最新代號，並強化汐止在地搜尋指令
            model = genai.GenerativeModel('models/gemini-flash-latest')
            prompt = (
                f"使用者目前位於座標 {lat}, {lon} (新北市汐止區)。"
                f"請推薦該座標方圓 2 公里內的 5 個「在地美食」或「景點」。"
                f"⚠️ 嚴格禁止推薦深坑、貓空、淡水或台北市中心等遙遠景點。"
                f"請優先推薦汐止觀光夜市、忠孝東路商圈、中興路附近或遠雄廣場的店家。"
                f"格式：名稱|介紹|類別|#標籤"
            )
            
            response = await asyncio.to_thread(model.generate_content, prompt)
            
            places = []
            if response.text:
                for line in response.text.strip().split('\n'):
                    parts = line.split('|')
                    if len(parts) >= 4:
                        places.append(LocationData(parts[0][:100], parts[1], parts[2], parts[3]))

            if places:
                view = View()
                view.add_item(PlaceSelect(places))
                await msg.edit(content=f"📍 汐止區 ({lat:.4f}, {lon:.4f}) 附近推薦：", view=view)
                return web.Response(text="OK")
            
            return web.Response(text="No Data")
        except Exception as e:
            print(f"Map Error: {e}")
            return web.Response(text=str(e), status=500)

async def setup(bot):
    await bot.add_cog(MapServer(bot))