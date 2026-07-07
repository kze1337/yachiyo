import discord
from discord.ext import commands
import random
import db

COMMAND_NAME = __name__.split('.')[-1]


class RankCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def add_xp(self, user: discord.User, guild, channel):
        if user.bot or not guild:
            return

        data      = db.load()
        udata     = db.get_user(data, guild.id, user.id)
        udata["xp"] += random.randint(5, 15)

        xp_needed = udata["level"] * 100
        if udata["xp"] >= xp_needed:
            udata["level"] += 1
            udata["xp"]    -= xp_needed
            udata["bal"]   += 500

            embed = discord.Embed(
                title="🎉 TĂNG CẤP! 🎉",
                description=(
                    f"Chúc mừng {user.mention} vươn lên **Level {udata['level']}**!\n"
                    f"Phần thưởng: **+500$** 💰"
                ),
                color=discord.Color.gold()
            )
            embed.set_thumbnail(url=user.display_avatar.url)
            await channel.send(embed=embed)

        db.save(data)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        await self.add_xp(message.author, message.guild, message.channel)

    @commands.Cog.listener()
    async def on_interaction(self, interaction: discord.Interaction):
        await self.add_xp(interaction.user, interaction.guild, interaction.channel)

    @commands.hybrid_command(name=COMMAND_NAME, description="Xem thẻ cấp độ của bạn")
    async def execute(self, ctx, user: discord.Member = None):
        if not ctx.guild:
            return await ctx.send("❌ Lệnh này chỉ dùng trong Server!", ephemeral=True)

        target   = user or ctx.author
        data     = db.load()
        guild_id = str(ctx.guild.id)
        user_id  = str(target.id)

        if guild_id not in data or user_id not in data[guild_id]:
            return await ctx.send(f"❌ {target.name} chưa có dữ liệu tại server này.", ephemeral=True)

        info      = data[guild_id][user_id]
        level     = info["level"]
        xp        = info["xp"]
        bal       = info.get("bal", 0)
        xp_needed = level * 100

        percent      = int((xp / xp_needed) * 10)
        progress_bar = "🟩" * percent + "⬜" * (10 - percent)

        embed = discord.Embed(title=f"Thẻ Cấp Độ của {target.name}", color=discord.Color.green())
        embed.set_thumbnail(url=target.display_avatar.url)
        embed.add_field(name="🏆 Level",    value=f"**{level}**", inline=True)
        embed.add_field(name="💰 Tài sản",  value=f"**{bal}$**",  inline=True)
        embed.add_field(name=f"✨ XP: {xp}/{xp_needed}", value=progress_bar, inline=False)
        await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(RankCog(bot))
