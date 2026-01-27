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
        # ✅ 重點 1：先告訴 Discord "收到，請稍等"，這樣就不會跳錯誤也不會發訊息
        await interaction.response.defer()

        data = load_data()
        owner = self.owner_name.value if self.owner_name.value else interaction.user.display_name
        
        new_item = {
            "task": self.task_content.value,
            "status": "TODO",
            "owner": owner
        }
        data["shared"].append(new_item)
        save_data(data)
        
        # 背景靜默更新面板
        await self.cog.update_dashboard()

# --- 🗑️ 2. 刪除任務的下拉選單 ---
class DeleteSelect(Select):
    def __init__(self, tasks, cog):
        self.cog = cog
        options = []
        for i, task in enumerate(tasks[:25]):
            label = task['task'][:25]
            desc = f"由 {task['owner']} 建立"
            options.append(discord.SelectOption(label=f"{i+1}. {label}", description=desc, value=str(i)))

        super().__init__(placeholder="請選擇要標記完成/刪除的任務...", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        index = int(self.values[0])
        data = load_data()
        
        task_name = "未知任務"
        if 0 <= index < len(data["shared"]):
            removed = data["shared"].pop(index)
            task_name = removed['task']
            save_data(data)
            await self.cog.update_dashboard()
            
            # ✅ 重點 2：不要發新訊息，而是「編輯」原本那個選單訊息
            # 把選單拿掉 (view=None)，改成顯示一行文字就好
            await interaction.response.edit_message(content=f"🗑️ 已移除：**{task_name}**", view=None)
        else:
            await interaction.response.edit_message(content="❌ 任務好像已經不在了！", view=None)

class DeleteView(View):
    def __init__(self, tasks, cog):
        super().__init__()
        self.add_item(DeleteSelect(tasks, cog))

# --- 🎛️ 3. 主控制面板按鈕 (永久駐留) ---
class DashboardView(View):
    def __init__(self, cog):
        super().__init__(timeout=None)
        self.cog = cog

    @discord.ui.button(label="➕ 新增任務", style=discord.ButtonStyle.success, custom_id="todo:add_btn", emoji="📝")
    async def add_callback(self, interaction: discord.Interaction, button: Button):
        # 彈出視窗必須用 send_modal，不能 defer
        await interaction.response.send_modal(AddTaskModal(self.cog))

    @discord.ui.button(label="🗑️ 完成/移除", style=discord.ButtonStyle.danger, custom_id="todo:del_btn", emoji="✅")
    async def delete_callback(self, interaction: discord.Interaction, button: Button):
        data = load_data()
        if not data["shared"]:
            # 這裡用 ephemeral=True 是合理的，因為是警告，且只有自己看得到
            return await interaction.response.send_message("💤 目前沒有任何任務喔！", ephemeral=True)
        
        # 這裡必須發送選單，但我們設定為 ephemeral (只有自己看得到)
        # 後續選擇後，上面的 DeleteSelect 會把它編輯掉，不會留垃圾
        await interaction.response.send_message("請選擇要移除的項目：", view=DeleteView(data["shared"], self.cog), ephemeral=True)

    @discord.ui.button(label="🔄", style=discord.ButtonStyle.secondary, custom_id="todo:refresh_btn")
    async def refresh_callback(self, interaction: discord.Interaction, button: Button):
        # ✅ 重點 3：重新整理時，完全不要說話，只轉圈圈然後更新背景
        await interaction.response.defer()
        await self.cog.update_dashboard()

# --- ⚙️ 4. 主要邏輯 (Cog) ---
class Todo(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def cog_load(self):
        self.bot.add_view(DashboardView(self))

    async def update_dashboard(self):
        channel = self.bot.get_channel(TODO_CHANNEL_ID)
        if not channel: return

        data = load_data()
        tasks = data.get("shared", [])
        msg_id = data.get("msg_id")

        embed = discord.Embed(title="🔥 團隊待辦事項看版", description="點擊下方按鈕來管理任務 👇", color=discord.Color.gold())
        
        if tasks:
            content_str = ""
            for i, item in enumerate(tasks):
                content_str += f"`{i+1}.` **{item['task']}** - *{item['owner']}*\n"
            embed.add_field(name="未完成任務", value=content_str, inline=False)
        else:
            embed.add_field(name="狀態", value="🎉 目前沒有待辦事項，大家辛苦了！", inline=False)

        embed.set_footer(text="即時同步中...")
        embed.timestamp = discord.utils.utcnow()

        if msg_id:
            try:
                msg = await channel.fetch_message(msg_id)
                await msg.edit(embed=embed, view=DashboardView(self))
                return
            except discord.NotFound:
                pass

        msg = await channel.send(embed=embed, view=DashboardView(self))
        data["msg_id"] = msg.id
        save_data(data)

    @commands.command()
    async def init_todo(self, ctx):
        if ctx.channel.id != TODO_CHANNEL_ID:
            return await ctx.send(f"❌ 請去 <#{TODO_CHANNEL_ID}> 使用此指令！")
        
        await ctx.message.delete()
        await self.update_dashboard()

async def setup(bot):
    await bot.add_cog(Todo(bot))