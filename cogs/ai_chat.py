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
        # 👇【修改處 1】請在這裡填入你要自動對話的「頻道 ID」(數字)
        # 如何取得 ID：Discord 設定 -> 進階 -> 開啟開發者模式 -> 右鍵點頻道 -> 複製 ID
        self.auto_chat_channel_id = 1463744730243399842
        # ---------------------------------------------------------

        if self.api_key:
            genai.configure(api_key=self.api_key)
            print("----- 正在搜尋可用模型 -----")
            available_models = []
            try:
                for m in genai.list_models():
                    if 'generateContent' in m.supported_generation_methods:
                        available_models.append(m.name)
            except Exception as e:
                print(f"❌ API 連線失敗: {e}")

            if 'models/gemini-1.5-flash' in available_models:
                target_model = 'gemini-1.5-flash'
            elif 'models/gemini-pro' in available_models:
                target_model = 'gemini-pro'
            elif available_models:
                target_model = available_models[0]
            else:
                target_model = 'gemini-pro'

            print(f"👉 決定使用模型: {target_model}")
            
            system_instruction = "你是一個 Discord 機器人助手。如果不清楚時間，請參考 User 訊息中提供的系統時間資訊。"
            
            self.model = genai.GenerativeModel(target_model)
            self.chat_session = self.model.start_chat(history=[])
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

    # 👇【修改處 2】監聽所有訊息的邏輯更新
    @commands.Cog.listener()
    async def on_message(self, message):
        # 1. 忽略機器人自己的訊息
        if message.author == self.bot.user: 
            return

        # 2. 判斷是否在「自動對話頻道」
        # 如果頻道 ID 吻合，且訊息不是空白 (例如只有圖片)
        if message.channel.id == self.auto_chat_channel_id and message.content.strip():
            
            # (選用) 如果訊息是指令開頭 (例如 !help)，就跳過，交給指令系統處理
            # 如果你不希望在該頻道使用任何指令，可以拿掉這兩行
            ctx = await self.bot.get_context(message)
            if ctx.valid: 
                return 

            # 開始 AI 回覆
            async with message.channel.typing():
                response = await self.get_ai_response(message.content)
                await message.reply(response)
            return # 處理完畢，結束函式

        # 3. 原有的 Mention (@機器人) 邏輯
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