import discord
from discord.ext import commands
import sys
from datetime import datetime

COMMAND_NAME = __name__.split('.')[-1]

class RestartCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(description='Khởi động lại bot', hidden=True)
    @commands.is_owner()
    async def restart(self, ctx):
        await ctx.send("🔄 Đang khởi động lại...")
        print(f"Restart time: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
        sys.exit(1)

    @restart.error
    async def restart_error(self, ctx, error):
        if isinstance(error, commands.NotOwner):
            await ctx.send("❌ Chỉ Owner mới có thể dùng lệnh này.")

async def setup(bot):
    await bot.add_cog(RestartCog(bot))