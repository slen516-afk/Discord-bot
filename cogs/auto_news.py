import discord
from discord.ext import commands, tasks
import feedparser
import urllib.parse
import datetime
import time # 👈 新增這個，用來處理時間格式

class AutoNews(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.target_channel_id = 1463387865202556979
        
        self.daily_news_task.start()

    def cog_unload(self):
        self.daily_news_task.cancel()

    # --- 抓新聞小幫手 (升級版) ---
    def get_rss_news(self, keyword=None):
        if keyword:
            encoded_keyword = urllib.parse.quote(keyword)
            rss_url = f"https://news.google.com/rss/search?q={encoded_keyword}&hl=zh-TW&gl=TW&ceid=TW:zh-Hant"
        else:
            rss_url = "https://news.google.com/rss?hl=zh-TW&gl=TW&ceid=TW:zh-Hant"

        feed = feedparser.parse(rss_url)
        articles = []
        for entry in feed.entries[:8]: # 取前 8 則
            # 處理時間：把怪怪的文字時間轉成電腦看得懂的 Timestamp
            # 處理時間 (加強防呆版：如果讀取失敗，就直接用現在時間，保證不當機)
            timestamp = int(time.time()) 
            if hasattr(entry, 'published_parsed') and entry.published_parsed:
                try:
                    timestamp = int(time.mktime(entry.published_parsed))
                except:
                    pass # 如果時間轉換失敗，就裝作沒事，繼續用預設時間

            articles.append({
                'title': entry.title,
                'link': entry.link,
                'timestamp': timestamp # 存成數字
            })
        return articles

    # --- 建立美化版 Embed 的函式 ---
    # --- 建立美化版 Embed 的函式 (防爆字修正版) ---
    def create_news_embed(self, articles, title_text):
        # 1. 先把所有新聞字串串接起來
        content_str = ""
        for i, item in enumerate(articles[:6]): # 限制最多顯示 6 則，避免太長
            time_str = f"<t:{item['timestamp']}:R>"
            content_str += f"{i+1}. **[{item['title']}]({item['link']})**\n"
            content_str += f"   └── 🕒 {time_str}\n\n"

        # 2. 建立 Embed
        embed = discord.Embed(
            title=title_text,
            # 把內容放在 description (容量 4096 字)，而不是 field (容量 1024 字)
            description=f"📅 **{datetime.date.today()} | 為您整理最新焦點**\n\n{content_str}",
            color=0x2b2d31 
        )
        
        # 3. 設定圖片與頁尾
        embed.set_thumbnail(url="https://cdn-icons-png.flaticon.com/512/2965/2965879.png")
        embed.set_footer(text="News powered by Google RSS", icon_url="https://upload.wikimedia.org/wikipedia/commons/thumb/d/da/Google_News_icon.svg/1200px-Google_News_icon.svg.png")
        
        return embed
        
        # 👇【視覺重點】設定一張好看的 Banner 圖片
        # 你可以換成任何你喜歡的圖片網址 (例如 Unsplash 的圖)
        embed.set_thumbnail(url="https://cdn-icons-png.flaticon.com/512/2965/2965879.png")
        
        # 內文排版優化
        content_str = ""
        for i, item in enumerate(articles):
            # Discord 的時間魔法：<t:123456:R> 會自動變成 "5分鐘前"
            time_str = f"<t:{item['timestamp']}:R>"
            
            # 使用 Markdown 語法： [標題](網址)
            # 加上 Emoji 讓畫面活潑一點
            content_str += f"{i+1}. **[{item['title']}]({item['link']})**\n"
            content_str += f"   └── 🕒 {time_str}\n\n"
        
        embed.add_field(name="📋 頭條快訊", value=content_str, inline=False)
        embed.set_footer(text="News powered by Google RSS", icon_url="https://upload.wikimedia.org/wikipedia/commons/thumb/d/da/Google_News_icon.svg/1200px-Google_News_icon.svg.png")
        
        return embed

    # --- 功能 1：手動指令 ---
    @commands.command()
    async def news(self, ctx, keyword=None):
        search_title = f"🔍 搜尋：{keyword}" if keyword else "📰 最新頭條新聞"
        await ctx.send(f"正在抓取 {search_title} ...")
        
        articles = self.get_rss_news(keyword)
        
        if not articles:
            await ctx.send("❌ 找不到相關新聞。")
            return

        embed = self.create_news_embed(articles, search_title)
        await ctx.send(embed=embed)

    # --- 功能 2：自動排程 ---
    broadcast_times = [
        datetime.time(hour=1, minute=0, second=0),  # 09:00
        datetime.time(hour=4, minute=0, second=0),  # 12:00
        datetime.time(hour=10, minute=0, second=0)  # 18:00
    ]

    @tasks.loop(time=broadcast_times)
    async def daily_news_task(self):
        channel = self.bot.get_channel(self.target_channel_id)
        if not channel: return

        now = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=8)
        if 5 <= now.hour < 11: greeting = "🌅 早安！"
        elif 11 <= now.hour < 14: greeting = "🍱 午安！"
        else: greeting = "🌆 晚上好！"

        articles = self.get_rss_news()
        if articles:
            embed = self.create_news_embed(articles, f"{greeting} 每日重點新聞")
            await channel.send(embed=embed)

    @daily_news_task.before_loop
    async def before_news_task(self):
        await self.bot.wait_until_ready()

async def setup(bot):
    await bot.add_cog(AutoNews(bot))