import discord
from discord.ext import commands
import google.generativeai as genai
import os
import datetime
import pytz # 👈 這是掌管時區的神器

class AIChat(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.api_key = os.getenv("GEMINI_API_KEY")
        self.model = None 
        
        if self.api_key:
            genai.configure(api_key=self.api_key)
            
            # --- 診斷與設定模型 (保持之前的邏輯) ---
            print("----- 正在搜尋可用模型 -----")
            available_models = []
            try:
                for m in genai.list_models():
                    if 'generateContent' in m.supported_generation_methods:
                        available_models.append(m.name)
            except Exception as e:
                print(f"❌ API 連線失敗: {e}")

            # 自動選擇模型
            if 'models/gemini-1.5-flash' in available_models:
                target_model = 'gemini-1.5-flash'
            elif 'models/gemini-pro' in available_models:
                target_model = 'gemini-pro'
            elif available_models:
                target_model = available_models[0]
            else:
                target_model = 'gemini-pro'

            print(f"👉 決定使用模型: {target_model}")
            
            # 設定 System Instruction (給 AI 的基本人設)
            # 告訴它：你是一個有用的助手，而且你會獲得當前的時間資訊
            system_instruction = "你是一個 Discord 機器人助手。如果不清楚時間，請參考 User 訊息中提供的系統時間資訊。"
            
            self.model = genai.GenerativeModel(target_model)
            self.chat_session = self.model.start_chat(history=[])
        else:
            print("⚠️ 警告：找不到 GEMINI_API_KEY")

    # --- 關鍵修改：獲取台灣時間 ---
    def get_taiwan_time(self):
        tz = pytz.timezone('Asia/Taipei')
        now = datetime.datetime.now(tz)
        # 格式範例：2026-01-22 星期四 14:30
        week_days = ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"]
        weekday_str = week_days[now.weekday()]
        return now.strftime(f"%Y-%m-%d {weekday_str} %H:%M")

    async def get_ai_response(self, user_text):
        if not self.model:
            return "❌ AI 腦袋還沒裝好"
        try:
            # 👇 【偷天換日大法】
            # 在使用者原本的話前面，偷偷加上「現在時間」的提示
            current_time = self.get_taiwan_time()
            prompt_with_time = f"(系統資訊: 現在台灣時間是 {current_time})\nUser 說: {user_text}"
            
            response = await self.chat_session.send_message_async(prompt_with_time)
            return response.text
        except Exception as e:
            return f"腦袋打結了... (錯誤: {e})"

    @commands.command()
    async def chat(self, ctx, *, message=None):
        if not message:
            await ctx.send("你想聊什麼？")
            return
        async with ctx.typing():
            response = await self.get_ai_response(message)
            if len(response) > 2000:
                await ctx.send(response[:2000])
                await ctx.send(response[2000:])
            else:
                await ctx.send(response)

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author == self.bot.user: return
        if self.bot.user.mentioned_in(message):
            clean_text = message.content.replace(f'<@{self.bot.user.id}>', '').strip()
            if not clean_text:
                await message.channel.send("叫我幹嘛？ 👀")
                return
            async with message.channel.typing():
                response = await self.get_ai_response(clean_text)
                await message.reply(response)

async def setup(bot):
    await bot.add_cog(AIChat(bot))