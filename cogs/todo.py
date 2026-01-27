import discord
from discord.ext import commands
from discord.ui import Button, View, Modal, TextInput, Select
import json
import os

# 🔒 設定你指定的頻道 ID
TODO_CHANNEL_ID = 1046731966516572240
DATA_FILE = "team_todo_list.json"

# --- 🛠️ 資料處理區 ---
def load_data():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return {"shared": [], "msg_id": None}
    return {"shared": [], "msg_id": None}

def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

# --- 📝 1. 新增任務的彈出視窗 (Modal) ---
class AddTaskModal(Modal, title="新增待辦事項"):
    task_content = TextInput(label="任務內容", placeholder="例如：修好 API 的 Bug", max_length=100)
    owner_name = TextInput(label="負責人/建立者", placeholder="你是誰？(選填)", required=False, max_length=20)

    def __init__(self, cog):
        super().__init__()
        self.cog = cog

    async def on_submit(self, interaction: discord.Interaction):
        data = load_data()
        owner = self.owner_name.value if self.owner_name.value else interaction.user.display_name
        
        new_item = {
            "task": self.task_content.value,
            "status": "TODO",
            "owner": owner
        }
        data["shared"].append(new_item)
        save_data(data)
        
        # 更新面板
        await self.cog.update_dashboard()
        await interaction.response.send_message(f"✅ 已新增：{self.task_content.value}", ephemeral=True)

# --- 🗑️ 2. 刪除任務的下拉選單 ---
class DeleteSelect(Select):
    def __init__(self, tasks, cog):
        self.cog = cog
        options = []
        # 只列出前 25 個任務 (Discord 限制)
        for i, task in enumerate(tasks[:25]):
            label = task['task'][:25]
            desc = f"由 {task['owner']} 建立"
            options.append(discord.SelectOption(label=f"{i+1}. {label}", description=desc, value=str(i)))

        super().__init__(placeholder="請選擇要標記完成/刪除的任務...", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        index = int(self.values[0])
        data = load_data()
        
        if 0 <= index < len(data["shared"]):
            removed = data["shared"].pop(index)
            save_data(data)
            await self.cog.update_dashboard()
            await interaction.response.send_message(f"🗑️ 已移除：{removed['task']}", ephemeral=True)
        else:
            await interaction.response.send_message("❌ 任務好像已經不在了！", ephemeral=True)

class DeleteView(View):
    def __init__(self, tasks, cog):
        super().__init__()
        self.add_item(DeleteSelect(tasks, cog))

# --- 🎛️ 3. 主控制面板按鈕 (永久駐留) ---
class DashboardView(View):
    def __init__(self, cog):
        super().__init__(timeout=None) # 這裡很重要，讓按鈕永遠有效
        self.cog = cog

    @discord.ui.button(label="➕ 新增任務", style=discord.ButtonStyle.success, custom_id="todo:add_btn", emoji="📝")
    async def add_callback(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_modal(AddTaskModal(self.cog))

    @discord.ui.button(label="🗑️ 完成/移除", style=discord.ButtonStyle.danger, custom_id="todo:del_btn", emoji="✅")
    async def delete_callback(self, interaction: discord.Interaction, button: Button):
        data = load_data()
        if not data["shared"]:
            return await interaction.response.send_message("💤 目前沒有任何任務喔！", ephemeral=True)
        
        # 傳送一個暫時的選單給使用者選
        await interaction.response.send_message("請選擇要移除的項目：", view=DeleteView(data["shared"], self.cog), ephemeral=True)

    @discord.ui.button(label="🔄 重新整理", style=discord.ButtonStyle.secondary, custom_id="todo:refresh_btn")
    async def refresh_callback(self, interaction: discord.Interaction, button: Button):
        await self.cog.update_dashboard()
        await interaction.response.send_message("已重新整理面板！", ephemeral=True)

# --- ⚙️ 4. 主要邏輯 (Cog) ---
class Todo(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # 當 Cog 載入時，嘗試恢復監聽按鈕
    async def cog_load(self):
        self.bot.add_view(DashboardView(self))

    # 更新面板的核心功能
    async def update_dashboard(self):
        channel = self.bot.get_channel(TODO_CHANNEL_ID)
        if not channel: return

        data = load_data()
        tasks = data.get("shared", [])
        msg_id = data.get("msg_id")

        # 製作 Embed 內容
        embed = discord.Embed(title="🔥 團隊待辦事項看版", description="點擊下方按鈕來管理任務 👇", color=discord.Color.gold())
        
        if tasks:
            content_str = ""
            for i, item in enumerate(tasks):
                content_str += f"`{i+1}.` **{item['task']}** - *{item['owner']}*\n"
            embed.add_field(name="未完成任務", value=content_str, inline=False)
        else:
            embed.add_field(name="狀態", value="🎉 目前沒有待辦事項，大家辛苦了！", inline=False)

        embed.set_footer(text="最後更新時間")
        embed.timestamp = discord.utils.utcnow()

        # 嘗試編輯舊訊息，如果找不到就發新的
        if msg_id:
            try:
                msg = await channel.fetch_message(msg_id)
                await msg.edit(embed=embed, view=DashboardView(self))
                return
            except discord.NotFound:
                pass # 舊訊息被刪了，準備發新的

        # 發送新訊息並記錄 ID
        msg = await channel.send(embed=embed, view=DashboardView(self))
        data["msg_id"] = msg.id
        save_data(data)

    # 初始化指令：只在第一次架設時用一次
    @commands.command()
    async def init_todo(self, ctx):
        if ctx.channel.id != TODO_CHANNEL_ID:
            return await ctx.send(f"❌ 請去 <#{TODO_CHANNEL_ID}> 使用此指令！")
        
        await ctx.message.delete() # 刪除使用者的指令
        await self.update_dashboard() # 建立面板

async def setup(bot):
    await bot.add_cog(Todo(bot))