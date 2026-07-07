import discord
from discord.ext import commands
import sys
from datetime import datetime

COMMAND_NAME = __name__.split('.')[-1]

class ShutdownCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(description='Tắt bot', hidden=True)
    @commands.is_owner()
    async def shutdown(self, ctx):
        await ctx.send("💤 Tạm biệt~")
        print(f"Shutdown time: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
        sys.exit(0)

    @shutdown.error
    async def shutdown_error(self, ctx, error):
        if isinstance(error, commands.NotOwner):
            await ctx.send("❌ Chỉ Owner mới có thể dùng lệnh này.")

async def setup(bot):
    await bot.add_cog(ShutdownCog(bot))