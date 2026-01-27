import discord
from discord.ext import commands
from discord.ui import Button, View, Modal, TextInput, Select
import json
import os
import uuid

# 🔒 設定你指定的頻道 ID
TODO_CHANNEL_ID = 1046731966516572240 
DATA_FILE = "team_todo_list.json"

# --- 🛠️ 資料處理區 (支援階層結構) ---
def load_data():
    default_data = {"shared": [], "msg_id": None}
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                # 資料結構遷移檢查：確保舊資料有 id 和 children 欄位
                for item in data.get("shared", []):
                    if "id" not in item: item["id"] = str(uuid.uuid4())[:8]
                    if "children" not in item: item["children"] = []
                    if "expanded" not in item: item["expanded"] = False
                return data
        except:
            return default_data
    return default_data

def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

# --- 📝 1. 新增主任務 Modal ---
class AddTaskModal(Modal, title="新增主任務"):
    task_content = TextInput(label="主任務內容", placeholder="例如：【重要時程】專題指導", max_length=100)
    owner_name = TextInput(label="負責人", placeholder="選填", required=False, max_length=20)

    def __init__(self, cog):
        super().__init__()
        self.cog = cog

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer()
        data = load_data()
        owner = self.owner_name.value if self.owner_name.value else interaction.user.display_name
        
        new_item = {
            "id": str(uuid.uuid4())[:8],
            "task": self.task_content.value,
            "status": "TODO",
            "owner": owner,
            "children": [], # 子任務列表
            "expanded": True # 預設展開方便看
        }
        data["shared"].append(new_item)
        save_data(data)
        await self.cog.update_dashboard()

# --- 📝 2. 新增子任務 (兩步驟：先選父任務 -> 再填內容) ---
class AddSubTaskModal(Modal, title="新增子項目"):
    subtask_content = TextInput(label="子項目內容", placeholder="例如：繳交文件", max_length=100)

    def __init__(self, cog, parent_id):
        super().__init__()
        self.cog = cog
        self.parent_id = parent_id

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer()
        data = load_data()
        
        # 尋找對應的父任務
        for item in data["shared"]:
            if item["id"] == self.parent_id:
                new_sub = {
                    "id": str(uuid.uuid4())[:8],
                    "task": self.subtask_content.value,
                    "status": "TODO",
                    "owner": interaction.user.display_name
                }
                item["children"].append(new_sub)
                item["expanded"] = True # 新增時自動展開
                break
        
        save_data(data)
        await self.cog.update_dashboard()

class SelectParentView(View):
    def __init__(self, tasks, cog):
        super().__init__()
        options = []
        for task in tasks[:25]:
            options.append(discord.SelectOption(label=task["task"][:25], value=task["id"], emoji="📂"))
        
        self.add_item(ParentSelect(options, cog))

class ParentSelect(Select):
    def __init__(self, options, cog):
        self.cog = cog
        super().__init__(placeholder="請選擇要加入到哪個主任務下...", options=options)

    async def callback(self, interaction: discord.Interaction):
        # 選完父任務後，跳出 Modal 填寫內容
        await interaction.response.send_modal(AddSubTaskModal(self.cog, self.values[0]))

# --- 📂 3. 展開/收起 控制器 ---
class ToggleExpandSelect(Select):
    def __init__(self, tasks, cog):
        self.cog = cog
        options = []
        for task in tasks[:25]:
            # 根據目前狀態顯示不同圖示
            icon = "▾" if task.get("expanded", False) else "▸"
            label = f"{icon} {task['task'][:23]}"
            options.append(discord.SelectOption(label=label, value=task["id"]))

        super().__init__(placeholder="點擊切換 展開/收起 狀態...", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer()
        data = load_data()
        target_id = self.values[0]
        
        for item in data["shared"]:
            if item["id"] == target_id:
                # 切換布林值
                item["expanded"] = not item.get("expanded", False)
                break
        
        save_data(data)
        await self.cog.update_dashboard()
        # 隱藏選單
        await interaction.edit_original_response(content="✅ 狀態已切換", view=None)

class ToggleView(View):
    def __init__(self, tasks, cog):
        super().__init__()
        self.add_item(ToggleExpandSelect(tasks, cog))

# --- 🗑️ 4. 完成/刪除 (扁平化顯示所有任務) ---
class DeleteSelect(Select):
    def __init__(self, data_list, cog):
        self.cog = cog
        options = []
        
        # 將樹狀結構扁平化以便列表
        # 格式：主任務 (ID) 或 主任務 > 子任務 (ID)
        count = 0
        for p in data_list:
            if count >= 25: break
            options.append(discord.SelectOption(
                label=f"🗑️ 主：{p['task'][:20]}", 
                value=f"parent:{p['id']}", 
                description="刪除此主任務與底下所有子項"
            ))
            count += 1
            if p.get("expanded", False): # 只有展開時才讓選子任務(避免列表太長)
                for c in p["children"]:
                    if count >= 25: break
                    options.append(discord.SelectOption(
                        label=f"　└ {c['task'][:20]}", 
                        value=f"child:{p['id']}:{c['id']}", 
                        description="刪除此子項目"
                    ))
                    count += 1

        super().__init__(placeholder="選擇要刪除的項目...", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer()
        data = load_data()
        action_type, *ids = self.values[0].split(":")
        
        if action_type == "parent":
            # 刪除主任務
            data["shared"] = [x for x in data["shared"] if x["id"] != ids[0]]
        elif action_type == "child":
            # 刪除子任務
            pid, cid = ids
            for p in data["shared"]:
                if p["id"] == pid:
                    p["children"] = [x for x in p["children"] if x["id"] != cid]
                    break
        
        save_data(data)
        await self.cog.update_dashboard()
        await interaction.edit_original_response(content="🗑️ 已移除項目", view=None)

class DeleteView(View):
    def __init__(self, tasks, cog):
        super().__init__()
        self.add_item(DeleteSelect(tasks, cog))

# --- 🎛️ 5. 主面板 ---
class DashboardView(View):
    def __init__(self, cog):
        super().__init__(timeout=None)
        self.cog = cog

    @discord.ui.button(label="➕ 主任務", style=discord.ButtonStyle.primary, custom_id="todo:add_parent", emoji="📁")
    async def add_parent(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_modal(AddTaskModal(self.cog))

    @discord.ui.button(label="➕ 子項目", style=discord.ButtonStyle.success, custom_id="todo:add_child", emoji="📄")
    async def add_child(self, interaction: discord.Interaction, button: Button):
        data = load_data()
        if not data["shared"]:
            return await interaction.response.send_message("❌ 請先建立主任務！", ephemeral=True)
        await interaction.response.send_message("請選擇要加入哪個主任務：", view=SelectParentView(data["shared"], self.cog), ephemeral=True)

    @discord.ui.button(label="📂 展開/收起", style=discord.ButtonStyle.secondary, custom_id="todo:toggle", emoji="🔻")
    async def toggle_expand(self, interaction: discord.Interaction, button: Button):
        data = load_data()
        if not data["shared"]: return await interaction.response.send_message("❌ 沒東西可以展開", ephemeral=True)
        await interaction.response.send_message("選擇要切換顯示的任務：", view=ToggleView(data["shared"], self.cog), ephemeral=True)

    @discord.ui.button(label="🗑️ 移除", style=discord.ButtonStyle.danger, custom_id="todo:del", emoji="🗑️")
    async def delete_item(self, interaction: discord.Interaction, button: Button):
        data = load_data()
        if not data["shared"]: return await interaction.response.send_message("💤 目前是空的", ephemeral=True)
        await interaction.response.send_message("請選擇要移除的項目：", view=DeleteView(data["shared"], self.cog), ephemeral=True)

    @discord.ui.button(label="🔄", style=discord.ButtonStyle.secondary, custom_id="todo:refresh")
    async def refresh(self, interaction: discord.Interaction, button: Button):
        await interaction.response.defer()
        await self.cog.update_dashboard()

# --- ⚙️ 主要邏輯 ---
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

        embed = discord.Embed(title="🚀 專案進度追蹤 (階層版)", description="使用下方按鈕管理專案結構", color=discord.Color.blue())
        
        content_lines = []
        if tasks:
            for i, p in enumerate(tasks):
                # 判斷箭頭方向
                arrow = "▾" if p.get("expanded", True) else "▸"
                # 主任務行
                content_lines.append(f"`{arrow} {p['task']}`")
                
                # 如果展開，顯示子任務
                if p.get("expanded", True):
                    if p["children"]:
                        for c in p["children"]:
                            content_lines.append(f"> 　└ ◻ {c['task']}")
                    else:
                        content_lines.append(f"> 　└ *[無子項目]*")
                
                content_lines.append("") # 空行分隔
        else:
            content_lines = ["🎉 目前沒有任務，請新增！"]

        # 組合內容 (防止過長)
        final_text = "\n".join(content_lines)
        if len(final_text) > 4000: final_text = final_text[:3900] + "\n...(內容過長)"
        
        embed.description = final_text
        embed.set_footer(text="點擊「📂 展開/收起」來控制箭頭")
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
        if ctx.channel.id != TODO_CHANNEL_ID: return
        await ctx.message.delete()
        await self.update_dashboard()

async def setup(bot):
    await bot.add_cog(Todo(bot))