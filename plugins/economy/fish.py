import discord
from discord.ext import commands
import random
import time
import db

COMMAND_NAME = __name__.split('.')[-1]

_RARITY_COLORS = {
    "Rác":        discord.Color.light_grey(),
    "Thường":     discord.Color.dark_grey(),
    "Khá":        discord.Color.green(),
    "Hiếm":       discord.Color.blue(),
    "Sử thi":     discord.Color.purple(),
    "Huyền thoại":discord.Color.gold(),
}

_FISHES = [
    {"name": "Giày rách",      "base_value":     10, "icon": "👞", "weight": 20, "rarity": "Rác",          "l_min": 15,  "l_max": 30},
    {"name": "Cành cây khô",   "base_value":     15, "icon": "🌿", "weight": 20, "rarity": "Rác",          "l_min": 20,  "l_max": 50},
    {"name": "Cá rô phi",      "base_value":    500, "icon": "🐟", "weight": 30, "rarity": "Thường",       "l_min": 10,  "l_max": 25},
    {"name": "Cá nóc",         "base_value":   1500, "icon": "🐡", "weight": 15, "rarity": "Khá",          "l_min": 20,  "l_max": 40},
    {"name": "Cá heo",         "base_value":   5000, "icon": "🐬", "weight":  8, "rarity": "Hiếm",         "l_min": 120, "l_max": 250},
    {"name": "Cá mập trắng",   "base_value":  20000, "icon": "🦈", "weight":  4, "rarity": "Sử thi",       "l_min": 300, "l_max": 600},
    {"name": "Rương kho báu",  "base_value":  50000, "icon": "💎", "weight":  2, "rarity": "Huyền thoại",  "l_min": 40,  "l_max": 60},
    {"name": "Đứt dây",        "base_value":      0, "icon": "💥", "weight": 10, "rarity": "None",         "l_min": 0,   "l_max": 0},
]


class FishCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(name=COMMAND_NAME, description="Câu cá kiếm tiền (Hồi chiêu: 30s)")
    async def execute(self, ctx):
        if not ctx.guild:
            return await ctx.send("❌ Lệnh này chỉ dùng trong Server!", ephemeral=True)

        data = db.load()
        user = db.get_user(data, ctx.guild.id, ctx.author.id)

        now      = time.time()
        cooldown = 30
        last     = user.get("last_fish", 0)

        if now - last < cooldown:
            left = int(cooldown - (now - last))
            return await ctx.send(
                f"⏳ Cần thủ hãy bình tĩnh! Thử lại sau **{left} giây**.",
                ephemeral=True
            )

        choice = random.choices(_FISHES, weights=[f["weight"] for f in _FISHES], k=1)[0]
        user["last_fish"] = now

        if choice["name"] == "Đứt dây":
            db.save(data)
            embed = discord.Embed(
                title="🎣 KẾT QUẢ ĐI CÂU",
                description=f"{choice['icon']} Kéo mạnh quá **Đứt dây** mất rồi! Bạn trắng tay.",
                color=discord.Color.red()
            )
            embed.set_footer(text=f"Số dư: {user['bal']}$")
            return await ctx.send(embed=embed)

        length      = round(random.uniform(choice["l_min"], choice["l_max"]), 1)
        bonus       = int((length / choice["l_max"]) * (choice["base_value"] * 0.2))
        final_value = choice["base_value"] + bonus
        user["bal"] += final_value
        db.save(data)

        embed = discord.Embed(
            title="🎣 KẾT QUẢ ĐI CÂU",
            description=f"Bạn vừa giật được một **{choice['name']}** {choice['icon']}!",
            color=_RARITY_COLORS.get(choice["rarity"], discord.Color.default())
        )
        embed.add_field(name="✨ Độ hiếm",  value=f"**{choice['rarity']}**", inline=True)
        embed.add_field(name="📏 Kích thước", value=f"**{length} cm**",       inline=True)
        embed.add_field(name="💰 Giá bán",  value=f"**{final_value}$**",      inline=True)
        embed.set_footer(text=f"Số dư: {user['bal']}$")
        await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(FishCog(bot))
