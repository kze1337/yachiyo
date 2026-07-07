import discord
from discord.ext import commands
import db

COMMAND_NAME = __name__.split('.')[-1]


class LeaderboardCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(name=COMMAND_NAME, description="Xem bảng xếp hạng Server này")
    async def execute(self, ctx):
        if not ctx.guild:
            return await ctx.send("❌ Lệnh này chỉ dùng trong Server!", ephemeral=True)

        data     = db.load()
        guild_id = str(ctx.guild.id)

        if guild_id not in data or not data[guild_id]:
            return await ctx.send("❌ Server này chưa có dữ liệu xếp hạng.", ephemeral=True)

        server = data[guild_id]
        top_bal   = sorted(server.items(), key=lambda x: x[1].get("bal",   0), reverse=True)[:10]
        top_level = sorted(server.items(), key=lambda x: (x[1].get("level", 0), x[1].get("xp", 0)), reverse=True)[:10]

        embed = discord.Embed(
            title=f"🏆 BẢNG XẾP HẠNG: {ctx.guild.name}",
            color=discord.Color.blurple()
        )

        bal_text   = "\n".join(f"**{i}.** <@{uid}> — **{info.get('bal', 0)}$**"          for i, (uid, info) in enumerate(top_bal,   1)) or "Chưa có"
        level_text = "\n".join(f"**{i}.** <@{uid}> — Level **{info.get('level', 0)}**"   for i, (uid, info) in enumerate(top_level, 1)) or "Chưa có"

        embed.add_field(name="💰 TOP ĐẠI GIA", value=bal_text,   inline=False)
        embed.add_field(name="⭐ TOP CẤP ĐỘ",  value=level_text, inline=False)
        await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(LeaderboardCog(bot))
