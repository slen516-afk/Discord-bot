import discord
from discord.ext import commands, tasks
import requests
import datetime
import urllib.parse

class Weather(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        
        # 👇 【這裡修改】地點清單 + 指定頻道
        # 格式：{"name": "名稱", "lat": 緯度, "lon": 經度, "channel_id": 頻道ID}
        # 這樣你就可以讓台北報在頻道A，新北報在頻道B (如果是同一個頻道，ID 填一樣的就好)
        self.daily_locations = [
            {
                "name": "台北市", 
                "lat": 25.0330, 
                "lon": 121.5654, 
                "channel_id": 1463412543128211641  # 👈 指定台北要在這裡報
            },
            {
                "name": "新北市", 
                "lat": 25.0143, 
                "lon": 121.4672, 
                "channel_id": 1463412543128211641  # 👈 指定新北要在這裡報 (可以跟上面不同)
            },
        ]

        # 啟動排程
        self.daily_forecast_task.start()

    def cog_unload(self):
        self.daily_forecast_task.cancel()

    # --- 小幫手 1: 取得經緯度 (手動查詢用) ---
    def get_coords(self, city_name):
        try:
            encoded_name = urllib.parse.quote(city_name)
            url = f"https://geocoding-api.open-meteo.com/v1/search?name={encoded_name}&count=1&language=zh&format=json"
            response = requests.get(url)
            data = response.json()
            if "results" in data and len(data["results"]) > 0:
                result = data["results"][0]
                return result["latitude"], result["longitude"], result["name"]
            return None, None, None
        except:
            return None, None, None

    # --- 小幫手 2: 取得天氣資料 ---
    def get_weather_data(self, lat, lon):
        try:
            url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&daily=weathercode,temperature_2m_max,temperature_2m_min,precipitation_probability_max&timezone=auto"
            response = requests.get(url)
            data = response.json()
            daily = data.get("daily", {})
            if not daily: return None

            return {
                "max": daily["temperature_2m_max"][0],
                "min": daily["temperature_2m_min"][0],
                "rain": daily["precipitation_probability_max"][0],
                "status": self.weather_code_to_text(daily["weathercode"][0])
            }
        except Exception as e:
            print(f"氣象抓取錯誤: {e}")
            return None

    # --- 小幫手 3: 天氣代碼轉文字 ---
    def weather_code_to_text(self, code):
        if code == 0: return "☀️ 晴朗"
        if code in [1, 2, 3]: return "🌤️ 多雲"
        if code in [45, 48]: return "🌫️ 有霧"
        if code in [51, 53, 55]: return "🌧️ 毛毛雨"
        if code in [61, 63, 65]: return "🌧️ 下雨"
        if code in [80, 81, 82]: return "⛈️ 雷陣雨"
        if code >= 95: return "⛈️ 雷雨交加"
        return "🌥️ 陰天"

    # ===============================
    #  功能 1: 手動查詢指令 (!weather 地區)
    # ===============================
    @commands.command()
    async def weather(self, ctx, *, city: str = None):
        if not city:
            # 沒輸入地點，就抓清單裡的第一個
            loc = self.daily_locations[0]
            city, lat, lon = loc["name"], loc["lat"], loc["lon"]
        else:
            await ctx.send(f"🔍 正在搜尋「{city}」的天氣...")
            lat, lon, real_name = self.get_coords(city)
            if not lat:
                await ctx.send(f"❌ 找不到「{city}」這個地方。")
                return
            city = real_name

        data = self.get_weather_data(lat, lon)
        if data:
            embed = discord.Embed(title=f"🌍 {city} 天氣預報", color=0x00b0f4)
            embed.add_field(name="天氣狀況", value=data['status'], inline=False)
            embed.add_field(name="氣溫", value=f"{data['min']}°C ~ {data['max']}°C", inline=True)
            embed.add_field(name="降雨機率", value=f"{data['rain']}%", inline=True)
            await ctx.send(embed=embed)

    # ===============================
    #  功能 2: 每天早上 06:00 自動預報 (支援指定頻道)
    # ===============================
    broadcast_time = datetime.time(hour=22, minute=0, second=0)

    @tasks.loop(time=broadcast_time)
    async def daily_forecast_task(self):
        # 跑迴圈，檢查每一個設定的地點
        for loc in self.daily_locations:
            
            # 👇 關鍵修改：從清單裡讀取該地點專屬的 Channel ID
            target_id = loc.get("channel_id")
            channel = self.bot.get_channel(target_id)
            
            if not channel:
                print(f"❌ 找不到頻道 ID: {target_id}")
                continue # 如果找不到頻道，就跳過這個，繼續下一個

            data = self.get_weather_data(loc["lat"], loc["lon"])
            
            if data:
                embed = discord.Embed(
                    title=f"📅 早安！今日天氣 ({loc['name']})",
                    color=0xff9900
                )
                embed.add_field(name="天氣狀況", value=data['status'], inline=False)
                embed.add_field(name="氣溫", value=f"{data['min']}°C ~ {data['max']}°C", inline=True)
                embed.add_field(name="降雨機率", value=f"{data['rain']}%", inline=True)
                
                if data['rain'] > 50:
                    embed.set_footer(text="☔ 記得帶傘！")
                
                await channel.send(embed=embed)

    @daily_forecast_task.before_loop
    async def before_forecast(self):
        await self.bot.wait_until_ready()

async def setup(bot):
    await bot.add_cog(Weather(bot))