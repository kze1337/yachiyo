import discord
from discord.ext import commands
import io

COMMAND_NAME = __name__.split('.')[-1]

class AvatarCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(description='Lấy avatar của bạn hoặc người được tag')
    async def avatar(self, ctx, user: discord.Member = None):
        user = user or ctx.author
        try:
            avatar_bytes = await user.display_avatar.read()
            file = discord.File(fp=io.BytesIO(avatar_bytes), filename=f"avatar_{user.id}.png")
            await ctx.send(file=file)
        except Exception as e:
            await ctx.send("❌ Không thể lấy avatar. Vui lòng thử lại!")

async def setup(bot):
    await bot.add_cog(AvatarCog(bot))