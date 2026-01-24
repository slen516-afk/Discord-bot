import discord
from discord.ext import commands
import google.generativeai as genai
from google.api_core import exceptions
import os
import datetime
import pytz
import aiohttp  # 用來下載圖片
import io
from dotenv import load_dotenv

class AIChat(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        load_dotenv(override=True)
        self.api_key = os.getenv("GEMINI_API_KEY")
        self.model = None 
        self.chat_session = None
        self.auto_chat_channel_id = 1463744730243399842

        if self.api_key:
            genai.configure(api_key=self.api_key)
            
            # 👇 這裡換成了你清單中最強、額度最穩的 Gemini 2.5 Flash
            target_model = 'models/gemini-2.5-flash'
            
            print(f"🚀 正在初始化模型: {target_model}")
            
            try:
                self.model = genai.GenerativeModel(
                    model_name=target_model,
                    system_instruction="你是一個 Discord 助手。回答簡潔。如果 User 傳送圖片，請根據圖片內容回應。"
                )
                self.chat_session = self.model.start_chat(history=[])
                print(f"✅ Gemini 初始化成功！使用模型: {target_model}")
            except Exception as e:
                print(f"❌ 初始化失敗: {e}")
        else:
            print("⚠️ 嚴重錯誤：找不到 API Key")

    def get_taiwan_time(self):
        tz = pytz.timezone('Asia/Taipei')
        now = datetime.datetime.now(tz)
        return now.strftime("%Y-%m-%d %H:%M")

    # 👇 新增：圖片下載處理功能
    async def process_attachments(self, message):
        image_parts = []
        if message.attachments:
            async with aiohttp.ClientSession() as session:
                for attachment in message.attachments:
                    # 檢查是否為圖片或 GIF
                    if any(ext in attachment.filename.lower() for ext in ['png', 'jpg', 'jpeg', 'gif', 'webp']):
                        async with session.get(attachment.url) as resp:
                            if resp.status == 200:
                                data = await resp.read()
                                # 轉換成 Gemini 看得懂的格式
                                image_parts.append({
                                    "mime_type": attachment.content_type or "image/jpeg",
                                    "data": data
                                })
        return image_parts

    async def get_ai_response(self, message, user_text):
        if not self.model or not self.chat_session:
            return "❌ AI 尚未就緒"
        
        try:
            current_time = self.get_taiwan_time()
            
            # 1. 處理圖片 (如果有)
            image_parts = await self.process_attachments(message)
            
            # 2. 組合提示詞
            prompt_content = [f"(系統時間: {current_time}) User 說: {user_text}"]
            
            # 3. 如果有圖片，加進去傳送內容
            if image_parts:
                prompt_content.extend(image_parts)
                print(f"📸 偵測到 {len(image_parts)} 張圖片，正在傳送給 AI...")

            # 4. 發送請求
            response = await self.chat_session.send_message_async(prompt_content)
            return response.text

        except exceptions.ResourceExhausted:
            return "💀 額度用完了 (429)，請稍等一下。"
        except Exception as e:
            print(f"❌ 錯誤: {e}")
            return "我看不懂這張圖或發生了錯誤..."

    @commands.command()
    async def chat(self, ctx, *, message=None):
        # 支援指令模式下附帶圖片
        user_msg = message if message else "（只傳了圖片）"
        if not message and not ctx.message.attachments:
            await ctx.send("你想聊什麼？")
            return
            
        async with ctx.typing():
            # 傳入 ctx.message 以便抓取附件
            response = await self.get_ai_response(ctx.message, user_msg)
            if len(response) > 2000:
                await ctx.send(response[:2000])
            else:
                await ctx.send(response)

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author == self.bot.user: return

        # 自動對話頻道邏輯
        is_auto_channel = (message.channel.id == self.auto_chat_channel_id)
        is_mentioned = self.bot.user.mentioned_in(message)

        if (is_auto_channel or is_mentioned) and (message.content.strip() or message.attachments):
            # 如果是 Mention，去掉 @機器人 的字串
            clean_text = message.content.replace(f'<@{self.bot.user.id}>', '').strip()
            
            async with message.channel.typing():
                response = await self.get_ai_response(message, clean_text)
                await message.reply(response)

async def setup(bot):
    await bot.add_cog(AIChat(bot))