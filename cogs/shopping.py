import discord
from discord.ext import commands
from discord.ui import View, Button
import aiohttp
import urllib.parse

# --- 翻頁控制器 (改為單張輪播模式) ---
class PChomeSingleEmbedView(View):
    def __init__(self, items):
        super().__init__(timeout=120)
        self.items = items
        self.current_page = 0
        self.items_per_page = 1  # 👈 關鍵修改：一次只顯示 1 筆，變身輪播圖！

    def get_embed(self):
        # 取得當前頁面的那 "1" 筆資料
        item = self.items[self.current_page]

        # 整理資料
        name = item.get("name", "未知商品")
        price = item.get("price", 0)
        prod_id = item.get("Id", "")
        pic_path = item.get("picB", item.get("picS", "")) # 優先抓大圖 (picB)
        image_url = f"https://cs-a.ecimg.tw{pic_path}" if pic_path else ""
        link = f"https://24h.pchome.com.tw/prod/{prod_id}"

        # 建立一張精美的卡片
        embed = discord.Embed(
            title=name,
            url=link,
            color=0xEA1717
        )
        # 價格放大顯示
        embed.description = f"### 💰 NT$ {price:,}"
        
        # 設定大圖 (因為一次只秀一張，用大圖比較爽)
        if image_url:
            embed.set_image(url=image_url)

        # 設定頁數資訊 (顯示目前是第幾件商品)
        total_items = len(self.items)
        embed.set_footer(text=f"📦 第 {self.current_page + 1} / {total_items} 件商品 | PChome 24h")

        return embed

    @discord.ui.button(label="◀ 上一個", style=discord.ButtonStyle.primary)
    async def prev_button(self, interaction: discord.Interaction, button: Button):
        if self.current_page > 0:
            self.current_page -= 1
        else:
            self.current_page = len(self.items) - 1 # 循環回到最後一個
            
        # 注意：因為只有一張 embed，所以這裡用 embed= (單數)
        await interaction.response.edit_message(embed=self.get_embed(), view=self)

    @discord.ui.button(label="▶ 下一個", style=discord.ButtonStyle.primary)
    async def next_button(self, interaction: discord.Interaction, button: Button):
        if self.current_page < len(self.items) - 1:
            self.current_page += 1
        else:
            self.current_page = 0 # 循環回到第一個
            
        await interaction.response.edit_message(embed=self.get_embed(), view=self)

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
        if message.author.bot: return
        if message.channel.id != self.shopping_channel_id: return

        keyword = message.content.strip()
        if not keyword or keyword.startswith("!"): return

        # 顯示搜尋中
        processing_msg = await message.channel.send(f"🔍 PChome 搜尋中：{keyword}...")

        items = await self.fetch_pchome_data(keyword)

        if not items:
            await processing_msg.edit(content=f"❌ 找不到「{keyword}」。", delete_after=5)
            return

        # 取前 20 筆
        items = items[:20]

        # 建立單張視圖
        view = PChomeSingleEmbedView(items)
        
        # 發送結果 (注意這裡用 embed= 單數)
        await processing_msg.delete()
        await message.channel.send(embed=view.get_embed(), view=view)

async def setup(bot):
    await bot.add_cog(Shopping(bot))