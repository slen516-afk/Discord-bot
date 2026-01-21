import discord
from discord.ext import commands
import sqlite3
import random

class Economy(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # 1.連結資料庫 (會自動在主目錄產生 economy.db 檔案)
        self.conn = sqlite3.connect("economy.db")
        self.cursor = self.conn.cursor()
        
        # 2.如果表格不存在，就建立一個 (欄位：使用者ID, 錢)
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                money INTEGER DEFAULT 0
            )
        """)
        self.conn.commit()

    # --- 小工具：確認使用者有沒有在資料庫裡 ---
    def check_user(self, user_id):
        self.cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        if self.cursor.fetchone() is None:
            # 如果沒資料，就新增一筆，預設 0 元
            self.cursor.execute("INSERT INTO users (user_id, money) VALUES (?, 0)", (user_id,))
            self.conn.commit()

    # --- 小工具：讀取餘額 ---
    def get_balance(self, user_id):
        self.check_user(user_id)
        self.cursor.execute("SELECT money FROM users WHERE user_id = ?", (user_id,))
        return self.cursor.fetchone()[0]

    # --- 小工具：修改餘額 (可以是正數或負數) ---
    def update_balance(self, user_id, amount):
        self.check_user(user_id)
        current = self.get_balance(user_id)
        new_balance = current + amount
        self.cursor.execute("UPDATE users SET money = ? WHERE user_id = ?", (new_balance, user_id))
        
        self.conn.commit()

    # ================= 指令區 =================

    @commands.command()
    async def balance(self, ctx):
        """查詢餘額"""
        money = self.get_balance(ctx.author.id)
        
        embed = discord.Embed(title="💰 你的錢包", color=0xf1c40f)
        embed.add_field(name="持有金額", value=f"${money}", inline=False)
        embed.set_thumbnail(url=ctx.author.display_avatar.url) # 顯示使用者頭貼
        
        await ctx.send(embed=embed)

    @commands.command()
    @commands.cooldown(1, 60, commands.BucketType.user) # 冷卻時間：每人 60 秒只能用一次
    async def work(self, ctx):
        """打工賺錢 (有冷卻時間)"""
        earnings = random.randint(10, 100) # 隨機賺 10~100 元
        self.update_balance(ctx.author.id, earnings)
        
        await ctx.send(f"🔨 {ctx.author.mention} 辛苦工作了一天，賺到了 **${earnings}** 元！")

    @commands.command()
    async def gamble(self, ctx, amount: int):
        """賭博指令：!gamble 100"""
        user_money = self.get_balance(ctx.author.id)

        # 防呆機制
        if amount <= 0:
            await ctx.send("❌ 賭注必須大於 0 元！")
            return
        if user_money < amount:
            await ctx.send("❌ 你的錢不夠！去 !work 打工吧！")
            return

        # 賭博邏輯 (50% 機率)
        if random.random() < 0.5:
            # 贏了
            win_amount = amount # 贏一倍
            self.update_balance(ctx.author.id, win_amount)
            await ctx.send(f"🎰 恭喜！你贏了 **${win_amount}**！現在有 **${user_money + win_amount}**")
        else:
            # 輸了
            self.update_balance(ctx.author.id, -amount)
            await ctx.send(f"💸 遺憾... 你輸了 **${amount}**。剩餘餘額：**${user_money - amount}**")

    # 處理打工還在冷卻時的錯誤
    @work.error
    async def work_error(self, ctx, error):
        if isinstance(error, commands.CommandOnCooldown):
            await ctx.send(f"⏳ 你太累了，請休息 {error.retry_after:.1f} 秒後再工作。")

async def setup(bot):
    await bot.add_cog(Economy(bot))