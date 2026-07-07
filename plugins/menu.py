import discord
from discord.ext import commands

COMMAND_NAME = __name__.split('.')[-1]

class MenuCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(description='Hiện tất cả lệnh của bot')
    async def menu(self, ctx):
        command_list = []
        for command in self.bot.commands:
            if not command.hidden:
                command_list.append(f"**{command.name}**: {command.description or 'Không có mô tả'}")
        
        menu_text = "📖 **Danh sách các lệnh của bot:**\n\n" + "\n".join(command_list)
        
        # ephemeral=True: Chỉ người nhập lệnh mới thấy (áp dụng cho lệnh Slash /)
        await ctx.send(menu_text, ephemeral=True)

async def setup(bot):
    await bot.add_cog(MenuCog(bot))