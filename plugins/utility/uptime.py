import discord
from discord.ext import commands
import psutil
import platform
import time
import pytz
from datetime import datetime

COMMAND_NAME = __name__.split('.')[-1]

class UptimeCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.start_time = time.time()

    def get_status_by_ping(self, ping):
        if ping < 200: return 'tốt'
        elif ping < 800: return 'bình thường'
        else: return 'xấu'

    # 1. Truyền thẳng biến COMMAND_NAME vào thuộc tính name=
    # 2. Tên hàm ở dưới bạn đặt là gì cũng được (ví dụ: execute, run, abc...)
    @commands.hybrid_command(name=COMMAND_NAME, description='Hiển thị thông tin hệ thống của bot')
    async def execute(self, ctx):
        tz = pytz.timezone('Asia/Ho_Chi_Minh')
        now = datetime.now(tz)
        
        mem = psutil.virtual_memory()
        uptime_seconds = int(time.time() - self.start_time)
        
        hours, remainder = divmod(uptime_seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        uptime_str = f"{hours:02d} giờ {minutes:02d} phút {seconds:02d} giây"
        
        ping_ms = round(self.bot.latency * 1000)
        bot_status = self.get_status_by_ping(ping_ms)
        
        reply_msg = f"""💮=[𝚄𝙿𝚃𝙸𝙼𝙴 𝚁𝙾𝙱𝙾𝚃]=💮
━━━━━━━━━━━━━━━
📅 Hôm nay là: {now.strftime('%d/%m/%Y')}
🕛 Thời gian: {now.strftime('%H:%M:%S')}
🤖 Tên bot: {self.bot.user.name}
⏰ Bot đã online được: {uptime_str}
↗️ Trạng thái bot: {bot_status}
📶 Ping: {ping_ms}ms
💻 RAM: {mem.used / (1024**3):.2f}GB / {mem.total / (1024**3):.2f}GB
🖥️ CPU: {psutil.cpu_count()} core(s) - {platform.processor()}
💾 Hệ điều hành: {platform.system()} {platform.release()} ({platform.machine()})"""

        await ctx.send(reply_msg)

async def setup(bot):
    await bot.add_cog(UptimeCog(bot))