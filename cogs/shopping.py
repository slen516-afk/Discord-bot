import discord
from discord.ext import commands
from discord.ui import View, Button
import aiohttp
import urllib.parse

# --- 翻頁控制器 (多卡片模式) ---
class PChomeMultiEmbedView(View):
    def __init__(self, items):
        super().__init__(timeout=120)
        self.items = items
        self.current_page = 0
        self.items_per_page = 5 # 一頁顯示 5 張小卡片

    def get_embeds(self):
        # 計算這一頁要顯示哪些資料 (例如 0~5)
        start_idx = self.current_page * self.items_per_page
        end_idx = start_idx + self.items_per_page
        page_items = self.items[start_idx:end_idx]

        embeds_list = []

        for i, item in enumerate(page_items):
            # 整理資料
            name = item.get("name", "未知商品")
            price = item.get("price", 0)
            prod_id = item.get("Id", "")
            pic_path = item.get("picS", item.get("picB", "")) # 優先抓小圖當縮圖
            image_url = f"https://cs-a.ecimg.tw{pic_path}" if pic_path else ""
            link = f"https://24h.pchome.com.tw/prod/{prod_id}"

            # 建立一張「小卡片」
            embed = discord.Embed(
                title=name,
                url=link,
                color=0xEA1717
            )
            # 設定價格 (放在描述裡)
            embed.description = f"💰 **NT$ {price:,}**"
            
            # 設定右側縮圖 (關鍵！每張卡片都有自己的圖)
            if image_url:
                embed.set_thumbnail(url=image_url)

            # 只在「最後一張卡片」顯示頁數資訊 (避免每張都有 footer 很亂)
            if i == len(page_items) - 1:
                total_pages = (len(self.items) + self.items_per_page - 1) // self.items_per_page
                embed.set_footer(text=f"第 {self.current_page + 1} / {total_pages} 頁 (共 {len(self.items)} 筆)")

            embeds_list.append(embed)

        return embeds_list

    @discord.ui.button(label="◀ 上一頁", style=discord.ButtonStyle.primary)
    async def prev_button(self, interaction: discord.Interaction, button: Button):
        if self.current_page > 0:
            self.current_page -= 1
            # 注意：這裡使用的是 embeds= (複數)，因為我們要回傳一整疊卡片
            await interaction.response.edit_message(embeds=self.get_embeds(), view=self)
        else:
            # 循環翻頁：如果已經是第一頁，按上一頁會跳到最後一頁
            total_pages = (len(self.items) + self.items_per_page - 1) // self.items_per_page
            self.current_page = total_pages - 1
            await interaction.response.edit_message(embeds=self.get_embeds(), view=self)

    @discord.ui.button(label="▶ 下一頁", style=discord.ButtonStyle.primary)
    async def next_button(self, interaction: discord.Interaction, button: Button):
        total_pages = (len(self.items) + self.items_per_page - 1) // self.items_per_page
        
        if self.current_page < total_pages - 1:
            self.current_page += 1
            await interaction.response.edit_message(embeds=self.get_embeds(), view=self)
        else:
            # 循環翻頁：如果已經是最後一頁，按下一頁會跳回第一頁
            self.current_page = 0
            await interaction.response.edit_message(embeds=self.get_embeds(), view=self)

    @discord.ui.button(label="🗑️ 關閉", style=discord.ButtonStyle.danger)
    async def close_button(self, interaction: discord.Interaction, button: Button):
        await interaction.message.delete()


# --- 主程式 ---
class Shopping(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # 👇 你的專用頻道 ID
        self.shopping_channel_id = 1464443840999194820 

    async def fetch_pchome_data(self, keyword):
        encoded_keyword = urllib.parse.quote(keyword)
        # 抓取 20 筆
        url = f"https://ecshweb.pchome.com.tw/search/v3.3/all/results?q={encoded_keyword}&page=1&sort=rnk/dc"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Referer": "https://24h.pchome.com.tw/"
        }
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers) as response:
                    if response.status == 200:
                        data = await response.json()
                        return data.get("prods", [])
                    else:
                        return None
        except Exception:
            return None

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot:
            return

        if message.channel.id != self.shopping_channel_id:
            return

        keyword = message.content.strip()
        if not keyword or keyword.startswith("!"):
            return

        # 顯示搜尋中
        processing_msg = await message.channel.send(f"🔍 PChome 圖文搜尋：{keyword}...")

        items = await self.fetch_pchome_data(keyword)

        if not items:
            await processing_msg.edit(content=f"❌ 找不到「{keyword}」。", delete_after=5)
            return

        # 取前 20 筆
        items = items[:20]

        # 建立多卡片視圖
        view = PChomeMultiEmbedView(items)
        
        # 刪除提示並發送結果 (注意這裡用 embeds=)
        await processing_msg.delete()
        await message.channel.send(embeds=view.get_embeds(), view=view)

async def setup(bot):
    await bot.add_cog(Shopping(bot))