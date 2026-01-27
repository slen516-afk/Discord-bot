import discord
from discord.ext import commands
import json
import os

# 🔒 設定你指定的頻道 ID
TODO_CHANNEL_ID = 1463412543128211641

class Todo(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.data_file = "team_todo_list.json" # 存檔名稱改成 team

    # 📥 讀取資料
    def load_data(self):
        if os.path.exists(self.data_file):
            try:
                with open(self.data_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except json.JSONDecodeError:
                return {}
        return {"shared": []} # 預設一個共用的 list

    # 💾 儲存資料
    def save_data(self, data):
        with open(self.data_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)

    # 🛡️ 安全檢查：確保指令只在正確的頻道使用
    async def cog_check(self, ctx):
        if ctx.channel.id != TODO_CHANNEL_ID:
            # 如果不是在指定頻道，就不回應 (或者你可以選擇回傳錯誤訊息)
            return False
        return True

    # 📝 指令群組
    @commands.group(name="todo", invoke_without_command=True)
    async def todo(self, ctx):
        embed = discord.Embed(title="🛡️ 團隊任務指令", color=discord.Color.gold())
        embed.add_field(name="➕ 新增任務", value="`!todo add <內容>`\n*例：!todo add 修復 API*", inline=False)
        embed.add_field(name="📋 查看清單", value="`!todo list`", inline=False)
        embed.add_field(name="✅ 完成任務", value="`!todo done <編號>`", inline=False)
        embed.add_field(name="🗑️ 刪除任務", value="`!todo del <編號>`", inline=False)
        embed.set_footer(text="這份清單是大家共用的喔！")
        await ctx.send(embed=embed)

    # 🔹 新增事項 (存入共用區)
    @todo.command(name="add")
    async def add_task(self, ctx, *, task: str):
        data = self.load_data()
        
        # 紀錄是誰新增的
        new_item = {
            "task": task, 
            "status": "TODO",
            "owner": ctx.author.display_name
        }
        
        data["shared"].append(new_item)
        self.save_data(data)
        
        await ctx.send(f"🆕 **{ctx.author.display_name}** 新增了任務：\n`{task}`")

    # 🔹 查看清單 (顯示共用區)
    @todo.command(name="list")
    async def list_tasks(self, ctx):
        data = self.load_data()
        tasks = data.get("shared", [])

        if not tasks:
            return await ctx.send("💤 目前團隊沒有待辦事項，大家可以休息了！")

        embed = discord.Embed(title="🔥 團隊待辦清單", color=discord.Color.orange())
        
        description = ""
        for i, item in enumerate(tasks):
            # 狀態圖示
            status_icon = "✅" if item["status"] == "DONE" else "⬜"
            
            # 格式化文字
            task_text = item['task']
            if item["status"] == "DONE":
                task_text = f"~~{task_text}~~"
            
            # 顯示格式： 1. ⬜ 任務名稱 (by 誰)
            description += f"`{i+1}.` {status_icon} **{task_text}** ({item['owner']})\n"

        embed.description = description
        await ctx.send(embed=embed)

    # 🔹 標記完成
    @todo.command(name="done")
    async def done_task(self, ctx, index: int):
        data = self.load_data()
        tasks = data.get("shared", [])

        if 0 < index <= len(tasks):
            tasks[index-1]["status"] = "DONE"
            self.save_data(data)
            await ctx.send(f"🎉 漂亮！**{ctx.author.display_name}** 完成了第 {index} 項任務！")
        else:
            await ctx.send("❌ 找不到這個編號，請檢查 `!todo list`")

    # 🔹 刪除事項
    @todo.command(name="del")
    async def delete_task(self, ctx, index: int):
        data = self.load_data()
        tasks = data.get("shared", [])

        if 0 < index <= len(tasks):
            removed = tasks.pop(index-1)
            self.save_data(data)
            await ctx.send(f"🗑️ 已刪除：**{removed['task']}**")
        else:
            await ctx.send("❌ 找不到這個編號。")

async def setup(bot):
    await bot.add_cog(Todo(bot))