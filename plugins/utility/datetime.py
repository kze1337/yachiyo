import discord
from discord.ext import commands
from datetime import datetime as dt
import pytz

COMMAND_NAME = __name__.split('.')[-1]

class DateTimeCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(description='Hiển thị ngày và giờ hiện tại')
    async def datetime(self, ctx):
        tz = pytz.timezone('Asia/Ho_Chi_Minh')
        now = dt.now(tz)
        current_date = now.strftime('%d/%m/%Y')
        current_time = now.strftime('%H:%M:%S')
        await ctx.send(f"📅 Current date: {current_date}\n🕛 Current time: {current_time}")

async def setup(bot):
    await bot.add_cog(DateTimeCog(bot))