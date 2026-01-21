# 檔案：main.py
import discord
import asyncio
import os
from discord.ext import commands
from dotenv import load_dotenv

# 1. 載入環境變數
load_dotenv()

# 2. 設定權限
intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

# --- 機器人事件 ---
@bot.event
async def on_ready():
    print(f"✅ 登入為 {bot.user}")
    print("-" * 50)

@bot.command()
async def hello(ctx):
    await ctx.send("Hello!")

@bot.command()
async def Whoyouare(ctx):
    await ctx.send("RYAN!")

# --- 自動載入 cogs 資料夾內的所有檔案 ---
# 這段程式碼會自己去 cogs 資料夾找檔案，
# 所以它會自動找到你剛建立的 video_scraping.py，不用改程式碼
async def load_extensions():
    if os.path.exists("./cogs"):
        for filename in os.listdir("./cogs"):
            if filename.endswith(".py"):
                try:
                    await bot.load_extension(f"cogs.{filename[:-3]}")
                    print(f"✅ 已載入模組: {filename}")
                except Exception as e:
                    print(f"❌ 無法載入 {filename}: {e}")
    else:
        print("⚠️ 找不到 cogs 資料夾")

# --- 系統啟動 ---
async def main():
    async with bot:
        await load_extensions()
        
        token = os.getenv("DISCORD_TOKEN")
        if not token:
            print("❌ 錯誤：找不到 Token！請檢查 .env")
            return
        
        print("🚀 準備啟動...")
        await bot.start(token) 

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass