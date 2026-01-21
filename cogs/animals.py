import discord
from discord.ext import commands
import requests

class Animals(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def cat(self, ctx):
        """隨機吸貓指令"""
        try:
            # 這是免費的 API，不用申請 Key
            response = requests.get("https://api.thecatapi.com/v1/images/search")
            data = response.json()
            image_url = data[0]['url'] # 抓圖片網址

            embed = discord.Embed(title="", color=0xff9900)
            embed.set_image(url=image_url) # 把圖片設定在 Embed 裡
            await ctx.send(embed=embed)
        except:
            await ctx.send("貓貓迷路了，請再試一次。")

    @commands.command()
    async def dog(self, ctx):
        """隨機吸狗指令"""
        try:
            response = requests.get("https://dog.ceo/api/breeds/image/random")
            data = response.json()
            image_url = data['message']

            embed = discord.Embed(title="", color=0x0099ff)
            embed.set_image(url=image_url)
            await ctx.send(embed=embed)
        except:
            await ctx.send("狗狗跑丟了，請再試一次。")

async def setup(bot):
    await bot.add_cog(Animals(bot))