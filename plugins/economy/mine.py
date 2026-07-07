import discord
from discord.ext import commands
import random
import db

COMMAND_NAME = __name__.split('.')[-1]


class MineCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(name=COMMAND_NAME, description="Đào mìn kiếm tiền")
    async def execute(self, ctx, bet: int):
        if not ctx.guild:
            return await ctx.send("❌ Lệnh này chỉ dùng trong Server!", ephemeral=True)
        if bet <= 0:
            return await ctx.send("❌ Số tiền cược phải lớn hơn 0!", ephemeral=True)
        if bet > 50_000_000:
            return await ctx.send("❌ Cược tối đa một lần là **50,000,000$**!", ephemeral=True)

        data = db.load()
        user = db.get_user(data, ctx.guild.id, ctx.author.id)

        if user["bal"] < bet:
            return await ctx.send(f"❌ Bạn không đủ tiền! Số dư: **{user['bal']}$**", ephemeral=True)

        result = random.choices(["boom", "normal", "jackpot"], weights=[40, 50, 10], k=1)[0]

        if result == "boom":
            user["bal"] -= bet
            msg = f"💣 **BÙM!** Bạn đạp trúng mìn và mất **{bet}$**!"
        elif result == "normal":
            user["bal"] += bet
            msg = f"⛏️ Đào thành công! Bạn nhận được **{bet}$** (x1)."
        else:
            user["bal"] += bet * 10
            msg = f"💎 **JACKPOT!** Đào trúng rương kho báu, nhận **{bet * 10}$**!"

        db.save(data)
        await ctx.send(f"{msg}\n💰 Số dư: **{user['bal']}$**")


async def setup(bot):
    await bot.add_cog(MineCog(bot))
