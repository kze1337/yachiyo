import discord
from discord.ext import commands
import db

COMMAND_NAME = __name__.split('.')[-1]


class PayCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(name=COMMAND_NAME, description="Chuyển tiền cho người khác trong server")
    async def execute(self, ctx, user: discord.Member, amount: int):
        if not ctx.guild:
            return await ctx.send("❌ Lệnh này chỉ dùng trong Server!", ephemeral=True)
        if user.bot or user == ctx.author:
            return await ctx.send("❌ Không thể chuyển tiền cho bot hoặc chính mình!", ephemeral=True)
        if amount <= 0:
            return await ctx.send("❌ Số tiền cần chuyển phải lớn hơn 0!", ephemeral=True)

        data   = db.load()
        sender = db.get_user(data, ctx.guild.id, ctx.author.id)
        target = db.get_user(data, ctx.guild.id, user.id)

        if sender["bal"] < amount:
            return await ctx.send(f"❌ Bạn không đủ tiền! Số dư: **{sender['bal']}$**", ephemeral=True)

        sender["bal"] -= amount
        target["bal"] += amount
        db.save(data)

        await ctx.send(
            f"💸 **GIAO DỊCH THÀNH CÔNG!**\n"
            f"**{ctx.author.name}** đã chuyển **{amount}$** cho **{user.name}**!"
        )


async def setup(bot):
    await bot.add_cog(PayCog(bot))
