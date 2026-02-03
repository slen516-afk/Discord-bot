# 檔案：cogs/video_scraping.py
import discord
from discord.ext import commands, tasks
import feedparser
import aiohttp # 👈 新增這個用來檢查網址

class VideoScraping(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        
        # 👇【設定 1】長影片通知頻道
        self.video_channel_id = 1463483175639584840 # youtube 影片通知頻道 ID
        #1463483175639584840
        
        # 👇【設定 2】Shorts 短影片通知頻道 (請填入新的頻道 ID)
        self.shorts_channel_id = 1464616199928414279 # youtube shorts 通知頻道 ID
        #1464616199928414279
        
        # 👇 YouTube 頻道清單
        self.youtube_channels = {
            "Chris Williamson(Modern Wisdom)": "UCIaH-gZIVC432YRjNVvnyCA",
            "Andrew Huberman": "UC2D2CMWXMOVWx7giW1n3LIg",
            "Hamza Ahmed": "UCWsslCoN3b_wBaFVWK_ye_A",
            "The Diary of a CEO": "UCGq-a57w-aPwyi3pW7XLiHw",
            "HealthyGamerGG":"UClHVl2N3jPEbkNJVx-ItQIQ",
            "Mark Manson":"UC0TnW9acNxqeojxXDMbohcA",
            "Prince Ea":"UCDgUAAHgsV2fFZQm2fIWBnA",
            "Alex Hormozi":"UCUyDOdBWhC1MCxEjC46d-zw",
            "Tech with Tim":"UC4JX40jDee_tINbkjycV4Sg",
            
            "Sajjaad Khader":"UC7zZ2-Q_oxbUaoMVL0z51wg",

            
            
        }
        
        # 記錄上次影片 ID
        self.latest_video_ids = {}

        # 啟動檢查排程
        self.check_youtube_task.start()

    def cog_unload(self):
        self.check_youtube_task.cancel()

    # 👇 新增：判斷是否為 Shorts 的功能
    async def check_is_shorts(self, video_id):
        url = f"https://www.youtube.com/shorts/{video_id}"
        try:
            # 禁止自動重新導向 (allow_redirects=False)
            # 如果是 Shorts，會回傳 200
            # 如果是長影片，YouTube 會回傳 303 並試圖導向 /watch
            async with aiohttp.ClientSession() as session:
                async with session.head(url, allow_redirects=False) as response:
                    return response.status == 200
        except:
            return False # 發生錯誤預設視為長影片

    # --- 排程：每 10 分鐘檢查一次 YouTube ---
    @tasks.loop(minutes=10)
    async def check_youtube_task(self):
        # 取得兩個目標頻道
        video_channel = self.bot.get_channel(self.video_channel_id)
        shorts_channel = self.bot.get_channel(self.shorts_channel_id)

        # 檢查頻道是否存在
        if not video_channel or not shorts_channel:
            print(f"❌ 錯誤：找不到頻道 ID，請檢查 video_channel_id 或 shorts_channel_id")
            # 這裡不 return，避免其中一個頻道錯了就全部不跑
        
        for name, channel_id in self.youtube_channels.items():
            url = f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"
            
            # 解析 RSS (feedparser 是同步的，量少時沒問題)
            feed = feedparser.parse(url)

            if feed.entries:
                latest_video = feed.entries[0]
                video_id = latest_video.yt_videoid
                video_link = latest_video.link
                video_title = latest_video.title

                # 邏輯 1. 剛開機 -> 記住最新影片，不發通知
                if channel_id not in self.latest_video_ids:
                    self.latest_video_ids[channel_id] = video_id
                
                # 邏輯 2. 有紀錄且 ID 不同 -> 發通知
                elif self.latest_video_ids[channel_id] != video_id:
                    print(f"🔍 發現新片: {video_title}，正在判斷類型...")
                    
                    # 判斷是 Shorts 還是長影片
                    is_shorts = await self.check_is_shorts(video_id)
                    
                    if is_shorts:
                        if shorts_channel:
                            print(f"👉 判定為 Shorts，發送到 Shorts 頻道")
                            # 為了讓 Discord 預覽正常顯示 Shorts，連結可以用 shorts 格式或原本的
                            await shorts_channel.send(f"📱 **{name}** 發布新 Shorts 了！\nhttps://www.youtube.com/shorts/{video_id}")
                    else:
                        if video_channel:
                            print(f"👉 判定為長影片，發送到 Video 頻道")
                            await video_channel.send(f"📢 **{name}** 發布新影片了！\n{video_link}")

                    # 更新紀錄
                    self.latest_video_ids[channel_id] = video_id

    @check_youtube_task.before_loop
    async def before_youtube_task(self):
        await self.bot.wait_until_ready()

async def setup(bot):
    await bot.add_cog(VideoScraping(bot))