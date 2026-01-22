# 檔案：cogs/video_scraping.py
import discord
from discord.ext import commands, tasks
import feedparser

class VideoScraping(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        
        # 👇 設定發送影片通知的頻道 ID
        self.target_channel_id = 1463483175639584840
        
        # 👇 YouTube 頻道清單
        self.youtube_channels = {
            "Modern Wisdom": "UCIaH-gZIVC432YRjNVvnyCA",
            "Andrew_Huberman": "UC2D2CMWXMOVWx7giW1n3LIg",
            "Hamza_Ahmed": "UCWsslCoN3b_wBaFVWK_ye_A",
            "The Diary of a CEO": "UCGq-a57w-aPwyi3pW7XLiHw",
            "HealthyGamerGG":"UClHVl2N3jPEbkNJVx-ItQIQ",
            "Mark Manson":"UC0TnW9acNxqeojxXDMbohcA",
            
        }
        
        # 記錄上次影片 ID
        self.latest_video_ids = {}

        # 啟動檢查排程
        self.check_youtube_task.start()

    def cog_unload(self):
        self.check_youtube_task.cancel()

    # --- 排程：每 10 分鐘檢查一次 YouTube ---
    @tasks.loop(minutes=10)
    async def check_youtube_task(self):
        channel = self.bot.get_channel(self.target_channel_id)
        if not channel:
            # 只有第一次找不到時印出錯誤，避免洗版
            print(f"❌ 無法找到頻道 ID: {self.target_channel_id}")
            return

        for name, channel_id in self.youtube_channels.items():
            url = f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"
            feed = feedparser.parse(url)

            if feed.entries:
                latest_video = feed.entries[0]
                video_id = latest_video.yt_videoid
                video_link = latest_video.link
                video_title = latest_video.title

                # 邏輯：
                # 1. 剛開機 -> 記住最新影片，不發通知
                if channel_id not in self.latest_video_ids:
                    self.latest_video_ids[channel_id] = video_id
                
                # 2. 有紀錄且 ID 不同 -> 發通知
                elif self.latest_video_ids[channel_id] != video_id:
                    print(f"發現新片！{name}: {video_title}")
                    await channel.send(f"📢 **{name}** 發布新影片了！\n{video_link}")
                    self.latest_video_ids[channel_id] = video_id

    @check_youtube_task.before_loop
    async def before_youtube_task(self):
        await self.bot.wait_until_ready()

async def setup(bot):
    await bot.add_cog(VideoScraping(bot))