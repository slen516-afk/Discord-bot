import discord
from discord.ext import commands
import google.generativeai as genai
import os
import datetime
import pytz 

class AIChat(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.api_key = os.getenv("GEMINI_API_KEY")
        self.model = None 
        
        # ---------------------------------------------------------
        # 👇 你的自動對話頻道 ID
        self.auto_chat_channel_id = 1463744730243399842
        # ---------------------------------------------------------

        if self.api_key:
            genai.configure(api_key=self.api_key)
            
            # ---------------------------------------------------------
            # 👇【策略切換】Flash 全滅，改用實驗版 'gemini-exp-1206'
            # 這個模型比 Flash 更聰明，而且額度池通常是分開的
            # ---------------------------------------------------------
            target_model = 'gemini-exp-1206'
            print(f"👉 嘗試設定模型為: {target_model}")
            
            sys_instruction = (
                "你是一個 Discord 機器人助手，你的核心模型是 Google Gemini Exp 1206。"
                "回答請保持簡潔有力。"
                "如果不清楚時間，請參考 User 訊息中提供的系統時間資訊。"
                "如果用戶詢問你的版本或模型，請明確回答你是 'Gemini Exp 1206'。"
            )
            
            try:
                self.model = genai.GenerativeModel(
                    target_model,
                    system_instruction=sys_instruction
                )
                self.chat_session = self.model.start_chat(history=[])
                print(f"✅ Gemini 模型初始化成功 ({target_model})")
            except Exception as e:
                print(f"❌ 模型初始化失敗: {e}")
        else:
            print("⚠️ 警告：找不到 GEMINI_API_KEY")

    def get_taiwan_time(self):
        tz = pytz.timezone('Asia/Taipei')
        now = datetime.datetime.now(tz)
        week_days = ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"]
        weekday_str = week_days[now.weekday()]
        return now.strftime(f"%Y-%m-%d {weekday_str} %H:%M")

    async def get_ai_response(self, user_text):
        if not self.model:
            return "❌ AI 腦袋還沒裝好"
        try:
            current_time = self.get_taiwan_time()
            prompt_with_time = f"(系統資訊: 現在台灣時間是 {current_time})\nUser 說: {user_text}"
            
            response = await self.chat_session.send_message_async(prompt_with_time)
            return response.text
        except Exception as e:
            error_msg = str(e)
            if "429" in error_msg:
                # 如果連這裡也 429，那就是整個 Google 帳號都被暫時鎖額度了
                print(f"❌ 額度全滅: {e}")
                return "💀 AI 徹底掛了 (此帳號今日額度全數用盡，請申請新的 API Key)"
            elif "404" in error_msg:
                return f"❌ 找不到模型 ({self.model.model_name if self.model else '未知'})"
            else:
                return f"腦袋打結了... (錯誤: {error_msg})"

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
        if message.author == self.bot.user: 
            return

        if message.channel.id == self.auto_chat_channel_id and message.content.strip():
            ctx = await self.bot.get_context(message)
            if ctx.valid: 
                return 

            async with message.channel.typing():
                response = await self.get_ai_response(message.content)
                await message.reply(response)
            return 

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