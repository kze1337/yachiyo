import discord
from discord.ext import commands
import random
import db

COMMAND_NAME = __name__.split('.')[-1]


def calculate_total(hand):
    total = 0
    aces  = 0
    for card in hand:
        if card["value"] in ("J", "Q", "K"):
            total += 10
        elif card["value"] == "A":
            aces += 1
        else:
            total += int(card["value"])
    for _ in range(aces):
        if total + 11 <= 21:
            total += 11
        else:
            total += 1
    return total


def format_hand(hand):
    return ", ".join(f"{c['value']}{c['suit']}" for c in hand)


class BlackjackView(discord.ui.View):
    def __init__(self, ctx, guild_id, user_id, bet, user_hand, dealer_hand, deck):
        super().__init__(timeout=60)
        self.ctx         = ctx
        self.guild_id    = guild_id
        self.user_id     = user_id
        self.bet         = bet
        self.user_hand   = user_hand
        self.dealer_hand = dealer_hand
        self.deck        = deck

    async def end_game(self, interaction, result_msg, win_multiplier=0):
        for child in self.children:
            child.disabled = True

        data = db.load()
        user = db.get_user(data, self.guild_id, self.user_id)

        if win_multiplier > 0:
            user["bal"] += int(self.bet * win_multiplier)
        db.save(data)

        u_total = calculate_total(self.user_hand)
        d_total = calculate_total(self.dealer_hand)

        embed = discord.Embed(
            title="🃏 BLACKJACK",
            description=result_msg,
            color=discord.Color.blue()
        )
        embed.add_field(name=f"👤 Bạn ({u_total})",      value=format_hand(self.user_hand),   inline=False)
        embed.add_field(name=f"🤖 Nhà cái ({d_total})", value=format_hand(self.dealer_hand), inline=False)
        embed.set_footer(text=f"Số dư mới: {user['bal']}$")

        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="Rút bài", style=discord.ButtonStyle.primary)
    async def hit_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if str(interaction.user.id) != self.user_id:
            return await interaction.response.send_message("❌ Đây không phải ván bài của bạn!", ephemeral=True)

        self.user_hand.append(self.deck.pop())
        u_total = calculate_total(self.user_hand)

        if u_total > 21:
            await self.end_game(interaction, f"❌ **BÙ (BUST)!** Bạn quá 21 điểm và mất **{self.bet}$**", 0)
        else:
            embed = discord.Embed(title="🃏 BLACKJACK", color=discord.Color.blue())
            embed.add_field(name=f"👤 Bạn ({u_total})", value=format_hand(self.user_hand), inline=False)
            embed.add_field(name="🤖 Nhà cái (?)", value=f"{self.dealer_hand[0]['value']}{self.dealer_hand[0]['suit']}, ❓", inline=False)
            await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="Dừng", style=discord.ButtonStyle.danger)
    async def stand_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if str(interaction.user.id) != self.user_id:
            return await interaction.response.send_message("❌ Đây không phải ván bài của bạn!", ephemeral=True)

        d_total = calculate_total(self.dealer_hand)
        while d_total < 17:
            self.dealer_hand.append(self.deck.pop())
            d_total = calculate_total(self.dealer_hand)

        u_total = calculate_total(self.user_hand)

        if d_total > 21:
            await self.end_game(interaction, f"🎉 **Nhà cái bù!** Bạn thắng **{self.bet}$** (x2)", 2)
        elif d_total > u_total:
            await self.end_game(interaction, f"❌ **Nhà cái cao hơn!** Bạn mất **{self.bet}$**", 0)
        elif d_total < u_total:
            await self.end_game(interaction, f"🎉 **Bạn cao hơn!** Bạn thắng **{self.bet}$** (x2)", 2)
        else:
            await self.end_game(interaction, f"🤝 **Hòa!** Bạn được hoàn lại **{self.bet}$**", 1)


class BlackjackCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(name=COMMAND_NAME, description="Chơi Blackjack (Xì dách) kiếm tiền")
    async def execute(self, ctx, bet: int):
        if not ctx.guild:
            return await ctx.send("❌ Lệnh này chỉ dùng trong Server!", ephemeral=True)
        if bet <= 0:
            return await ctx.send("❌ Số tiền cược phải lớn hơn 0!", ephemeral=True)
        if bet > 50_000_000:
            return await ctx.send("❌ Cược tối đa một lần là **50,000,000$**!", ephemeral=True)

        guild_id = str(ctx.guild.id)
        user_id  = str(ctx.author.id)

        data = db.load()
        user = db.get_user(data, guild_id, user_id)

        if user["bal"] < bet:
            return await ctx.send(f"❌ Bạn không đủ tiền! Số dư: **{user['bal']}$**", ephemeral=True)

        # Deduct bet upfront
        user["bal"] -= bet
        db.save(data)

        # Build deck
        suits  = ["♠", "♥", "♣", "♦"]
        values = ["2","3","4","5","6","7","8","9","10","J","Q","K","A"]
        deck   = [{"suit": s, "value": v} for s in suits for v in values]
        random.shuffle(deck)

        user_hand   = [deck.pop(), deck.pop()]
        dealer_hand = [deck.pop(), deck.pop()]
        u_total     = calculate_total(user_hand)

        # Natural blackjack
        if u_total == 21:
            data = db.load()
            user = db.get_user(data, guild_id, user_id)
            user["bal"] += int(bet * 2.5)
            db.save(data)

            embed = discord.Embed(
                title="🃏 BLACKJACK",
                description=f"🎉 **XÌ DÁCH!** Bạn thắng **{int(bet * 1.5)}$**",
                color=discord.Color.gold()
            )
            embed.add_field(name="👤 Bạn (21)",                          value=format_hand(user_hand),                      inline=False)
            embed.add_field(name=f"🤖 Nhà cái ({calculate_total(dealer_hand)})", value=format_hand(dealer_hand), inline=False)
            embed.set_footer(text=f"Số dư mới: {user['bal']}$")
            return await ctx.send(embed=embed)

        view  = BlackjackView(ctx, guild_id, user_id, bet, user_hand, dealer_hand, deck)
        embed = discord.Embed(title="🃏 BLACKJACK", color=discord.Color.blue())
        embed.add_field(name=f"👤 Bạn ({u_total})", value=format_hand(user_hand), inline=False)
        embed.add_field(name="🤖 Nhà cái (?)", value=f"{dealer_hand[0]['value']}{dealer_hand[0]['suit']}, ❓", inline=False)
        await ctx.send(embed=embed, view=view)


async def setup(bot):
    await bot.add_cog(BlackjackCog(bot))
