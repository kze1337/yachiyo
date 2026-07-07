import discord
from discord.ext import commands
import asyncio
import yt_dlp
import os
import random
from collections import deque

COMMAND_NAME = __name__.split('.')[-1]
FFMPEG_PATH = "ffmpeg.exe" if os.name == "nt" else "ffmpeg"

# =========================
# YTDL CONFIG
# =========================
ytdl_format_options = {
    'format': 'bestaudio/best',
    'outtmpl': 'temp/%(id)s.%(ext)s',
    'restrictfilenames': True,
    'noplaylist': False,
    'nocheckcertificate': True,
    'ignoreerrors': False,
    'logtostderr': False,
    'quiet': True,
    'no_warnings': True,
    'default_search': 'ytsearch',
    'source_address': '0.0.0.0',
    'socket_timeout': 15,
    'extract_flat': False,
    'extractor_args': {
        'youtube': {
            'player_client': ['android']
        }
    }
}

ffmpeg_options = {
    'before_options':
        '-reconnect 1 '
        '-reconnect_streamed 1 '
        '-reconnect_delay_max 5',
    'options': '-vn'
}

ytdl = yt_dlp.YoutubeDL(ytdl_format_options)

EMBED_COLOR = 0x2F3136


# =========================
# SONG OBJECT
# =========================
class Song:
    def __init__(self, data):
        self.title     = data.get("title")
        self.url       = data.get("webpage_url")
        self.stream    = data.get("url")
        self.duration  = data.get("duration")
        self.thumbnail = data.get("thumbnail")
        self.requester = None


# =========================
# MUSIC PLAYER
# =========================
class GuildMusicPlayer:
    def __init__(self, bot, guild):
        self.bot          = bot
        self.guild        = guild
        self.queue        = asyncio.Queue()
        self.next         = asyncio.Event()
        self.current      = None
        self.voice        = None
        self.loop         = False
        self.volume       = 0.5
        self.text_channel = None

        # The single persistent Now Playing message
        self._np_message: discord.Message | None = None

        self.player_task = bot.loop.create_task(self.player_loop())

    # --------------------------------------------------
    # Build the Now Playing embed
    # --------------------------------------------------
    def _build_np_embed(self, song: Song) -> discord.Embed:
        embed = discord.Embed(
            title="🎵 Now Playing",
            description=f"**{song.title}**",
            color=EMBED_COLOR
        )
        if song.thumbnail:
            embed.set_thumbnail(url=song.thumbnail)
        embed.add_field(name="Requested By", value=song.requester.mention)

        # Show queue size so users know what's coming
        upcoming = self.queue.qsize()
        if upcoming:
            embed.set_footer(text=f"{upcoming} bài tiếp theo trong queue")

        return embed

    # --------------------------------------------------
    # Update or create the Now Playing message
    # --------------------------------------------------
    async def _update_np_message(self, song: Song) -> None:
        if not self.text_channel:
            return

        embed = self._build_np_embed(song)

        # Try to edit the existing message first
        if self._np_message:
            try:
                await self._np_message.edit(embed=embed)
                return
            except (discord.NotFound, discord.HTTPException):
                # Message was deleted or uneditable — fall through to send a new one
                self._np_message = None

        # Send a fresh message and remember it
        try:
            self._np_message = await self.text_channel.send(embed=embed)
        except Exception as e:
            print(f"[NP MESSAGE] {e}")

    # --------------------------------------------------
    # Delete the Now Playing message when music stops
    # --------------------------------------------------
    async def _clear_np_message(self) -> None:
        if self._np_message:
            try:
                await self._np_message.delete()
            except Exception:
                pass
            self._np_message = None

    # --------------------------------------------------
    # Main player loop
    # --------------------------------------------------
    async def player_loop(self):
        while True:
            self.next.clear()

            try:
                song = await asyncio.wait_for(self.queue.get(), timeout=300)
            except asyncio.TimeoutError:
                await self._clear_np_message()
                if self.voice:
                    await self.voice.disconnect()
                return

            self.current = song
            print(f"[RADAR 4] Chuẩn bị phát nhạc bằng FFmpeg: {song.title}")

            source = discord.PCMVolumeTransformer(
                discord.FFmpegPCMAudio(
                    song.stream,
                    executable=FFMPEG_PATH,
                    **ffmpeg_options
                ),
                volume=self.volume
            )

            def after_playing(error):
                if error:
                    print(f"[RADAR 5] ❌ FFmpeg GẶP LỖI: {error}")
                else:
                    print("[RADAR 5] ✅ Bài hát kết thúc bình thường.")
                self.bot.loop.call_soon_threadsafe(self.next.set)

            try:
                self.voice.play(source, after=after_playing)
                print("[RADAR 4] ✅ FFmpeg đang chạy mượt mà!")
            except Exception as e:
                print(f"[RADAR 4] ❌ LỖI FFmpeg: {e}")
                self.next.set()

            # Update (or create) the single Now Playing message
            await self._update_np_message(song)

            await self.next.wait()

            if self.loop:
                await self.queue.put(song)


# =========================
# MUSIC COG
# =========================
class MusicCog(commands.Cog):

    def __init__(self, bot):
        self.bot     = bot
        self.players = {}

    def get_player(self, guild) -> GuildMusicPlayer:
        if guild.id not in self.players:
            self.players[guild.id] = GuildMusicPlayer(self.bot, guild)
        return self.players[guild.id]

    async def connect_voice(self, ctx) -> discord.VoiceClient | None:
        if not ctx.author.voice:
            return None

        channel = ctx.author.voice.channel
        permissions = channel.permissions_for(ctx.me)

        if not permissions.connect or not permissions.speak:
            await ctx.send("❌ Bot không có quyền vào hoặc nói trong kênh này!")
            return None

        if ctx.voice_client:
            return ctx.voice_client

        try:
            print(f"[RADAR 1] Cố gắng kết nối tới: {channel.id}")
            vc = await channel.connect(timeout=20, reconnect=True, self_deaf=True)
            print("[RADAR 1] ✅ Kết nối thành công!")
            return vc
        except Exception as e:
            print(f"[RADAR 1] ❌ LỖI KẾT NỐI: {e}")
            return None

    # =========================
    # COMMANDS
    # =========================

    @commands.hybrid_command(name="play", description="Play music")
    async def play(self, ctx, *, query: str):
        if ctx.interaction:
            await ctx.defer()

        if not ctx.author.voice:
            return await ctx.send("❌ Bạn phải vào voice channel trước!")

        vc = await self.connect_voice(ctx)
        if not vc:
            return await ctx.send("❌ Kẹt ở bước vào Voice. Hãy kiểm tra lại Terminal!")

        player = self.get_player(ctx.guild)
        player.voice        = vc
        player.text_channel = ctx.channel

        try:
            print(f"[RADAR 2] Đang tải dữ liệu từ YouTube cho: {query}")
            data = await self.bot.loop.run_in_executor(
                None,
                lambda: ytdl.extract_info(query, download=False)
            )
            print("[RADAR 2] ✅ Tải dữ liệu YouTube thành công!")
        except Exception as e:
            print(f"[RADAR 2] ❌ LỖI YOUTUBE: {e}")
            return await ctx.send("❌ Không thể tải bài hát do bị chặn hoặc lỗi mạng.")

        songs = []
        if 'entries' in data:
            for entry in data['entries']:
                if not entry:
                    continue
                song           = Song(entry)
                song.requester = ctx.author
                songs.append(song)
                await player.queue.put(song)
        else:
            song           = Song(data)
            song.requester = ctx.author
            songs.append(song)
            await player.queue.put(song)

        print(f"[RADAR 3] Đã thêm {len(songs)} bài hát vào hàng đợi!")

        embed = discord.Embed(
            title="✅ Added To Queue",
            description="\n".join([f"• {s.title}" for s in songs[:10]]),
            color=EMBED_COLOR
        )
        if len(songs) > 10:
            embed.set_footer(text=f"+{len(songs) - 10} more...")

        await ctx.send(embed=embed)

    @commands.hybrid_command(name="join", description="Mời Yachoo vào kênh thoại")
    async def join(self, ctx):
        if not ctx.author.voice:
            return await ctx.send("❌ Bạn phải vào một kênh thoại trước thì mình mới biết đường vào chung chứ! 😆")

        # Gọi hàm connect_voice đã được định nghĩa sẵn ở trên
        vc = await self.connect_voice(ctx)
        if vc:
            await ctx.send(f"🌸 Mình đã có mặt tại **{ctx.author.voice.channel.name}** rồi nè! Gọi lệnh play để mình hát cho bạn nghe nha! 🎵✨")

    @commands.hybrid_command(name="leave", aliases=["dc", "disconnect"], description="Bảo Yachoo rời khỏi kênh thoại")
    async def leave(self, ctx):
        vc = ctx.voice_client
        if not vc:
            return await ctx.send("❌ Ơ kìa, mình có đang ở trong kênh thoại nào đâu... 😅")

        # Dọn dẹp hàng đợi và tắt nhạc y hệt như lệnh stop
        player = self.get_player(ctx.guild)
        player.queue = asyncio.Queue()
        player.loop  = False
        vc.stop()

        await player._clear_np_message()
        await vc.disconnect()
        await ctx.send("👋 Mình rời kênh thoại đây! Khi nào muốn nghe nhạc tiếp thì lại gọi mình nhé! 🥰🌙")

    @commands.hybrid_command(name="skip", description="Skip current song")
    async def skip(self, ctx):
        vc = ctx.voice_client
        if not vc or not vc.is_playing():
            return await ctx.send("❌ Không có nhạc đang phát.")
        vc.stop()
        await ctx.send("⏭️ Đã skip bài hát.")

    @commands.hybrid_command(name="stop", description="Stop music")
    async def stop(self, ctx):
        vc = ctx.voice_client
        if not vc:
            return await ctx.send("❌ Bot không ở voice.")

        player = self.get_player(ctx.guild)
        player.queue = asyncio.Queue()
        player.loop  = False
        vc.stop()

        await player._clear_np_message()
        await vc.disconnect()
        await ctx.send("👋 Đã dừng nhạc và rời voice.")

    @commands.hybrid_command(name="pause")
    async def pause(self, ctx):
        vc = ctx.voice_client
        if vc and vc.is_playing():
            vc.pause()
            await ctx.send("⏸️ Đã pause.")

    @commands.hybrid_command(name="resume")
    async def resume(self, ctx):
        vc = ctx.voice_client
        if vc and vc.is_paused():
            vc.resume()
            await ctx.send("▶️ Đã resume.")

    @commands.hybrid_command(name="volume")
    async def volume(self, ctx, volume: int):
        if volume < 0 or volume > 100:
            return await ctx.send("❌ Volume từ 0-100.")
        player         = self.get_player(ctx.guild)
        player.volume  = volume / 100
        if ctx.voice_client and ctx.voice_client.source:
            ctx.voice_client.source.volume = volume / 100
        await ctx.send(f"🔊 Volume: {volume}%")

    @commands.hybrid_command(name="nowplaying", aliases=["np"])
    async def nowplaying(self, ctx):
        player = self.get_player(ctx.guild)
        if not player.current:
            return await ctx.send("❌ Không có bài hát.")
        # Jump to the persistent message if it exists, otherwise send fresh
        await player._update_np_message(player.current)

    @commands.hybrid_command(name="queue")
    async def queue_cmd(self, ctx):
        player   = self.get_player(ctx.guild)
        upcoming = list(player.queue._queue)
        if not upcoming:
            return await ctx.send("❌ Queue trống.")

        desc = ""
        for i, song in enumerate(upcoming[:15], start=1):
            desc += f"`{i}` {song.title}\n"

        embed = discord.Embed(
            title="🎶 Music Queue",
            description=desc,
            color=EMBED_COLOR
        )
        if len(upcoming) > 15:
            embed.set_footer(text=f"+{len(upcoming) - 15} more songs...")

        await ctx.send(embed=embed)

    @commands.hybrid_command(name="loop")
    async def loop(self, ctx):
        player      = self.get_player(ctx.guild)
        player.loop = not player.loop
        await ctx.send("🔁 Loop enabled." if player.loop else "⏹️ Loop disabled.")

    @commands.hybrid_command(name="shuffle")
    async def shuffle(self, ctx):
        player = self.get_player(ctx.guild)
        queue  = list(player.queue._queue)
        if len(queue) < 2:
            return await ctx.send("❌ Không đủ bài để shuffle.")
        random.shuffle(queue)
        player.queue._queue = deque(queue)
        await ctx.send("🔀 Đã shuffle queue.")


# =========================
# SETUP
# =========================
async def setup(bot):
    if not os.path.exists("temp"):
        os.makedirs("temp")
    await bot.add_cog(MusicCog(bot))