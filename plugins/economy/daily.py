import discord
from discord.ext import commands
import time
import db

COMMAND_NAME = __name__.split('.')[-1]


class DailyCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(name=COMMAND_NAME, description="Nhận phần thưởng 2000$ mỗi ngày")
    async def execute(self, ctx):
        if not ctx.guild:
            return await ctx.send("❌ Lệnh này chỉ có thể dùng trong Server!", ephemeral=True)

        data = db.load()
        user = db.get_user(data, ctx.guild.id, ctx.author.id)

        now      = time.time()
        cooldown = 86400
        last     = user.get("last_daily", 0)

        if now - last < cooldown:
            left = cooldown - (now - last)
            h, r = divmod(int(left), 3600)
            m, s = divmod(r, 60)
            return await ctx.send(
                f"⏳ Bạn đã nhận quà rồi! Quay lại sau **{h}h {m}p {s}s**.",
                ephemeral=True
            )

        user["bal"]        += 2000
        user["last_daily"]  = now
        db.save(data)

        await ctx.send(
            f"🎁 **THƯỞNG MỖI NGÀY!** Bạn vừa nhận **2000$**. "
            f"Số dư: **{user['bal']}$**"
        )


async def setup(bot):
    await bot.add_cog(DailyCog(bot))
