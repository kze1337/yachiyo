import discord
from discord.ext import commands
import os
import json
from dotenv import load_dotenv

# Load Token và Config
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

with open('config.json', 'r', encoding='utf-8') as f:
    config = json.load(f)

# Cấp quyền (Intents) cho bot
intents = discord.Intents.default()
intents.message_content = True

# Khởi tạo bot
bot = commands.Bot(command_prefix=config['prefix'], intents=intents)

@bot.event
async def on_ready():
    # Cài đặt trạng thái (Status/Activity) từ config
    activity_type = getattr(discord.ActivityType, config['presence']['activity_type'], discord.ActivityType.playing)
    status = getattr(discord.Status, config['presence']['status'], discord.Status.online)
    
    await bot.change_presence(
        status=status, 
        activity=discord.Activity(type=activity_type, name=config['presence']['activity_name'])
    )
    
    print(f'🤖 Đã đăng nhập thành công: {bot.user.name}')
    print('---------------------------------')

# Lệnh đồng bộ Slash Command (Chỉ Owner mới dùng được)
@bot.command(help='Đồng bộ lệnh Slash lên Discord.')
@commands.is_owner()
async def sync(ctx):
    # 1. Gửi tin nhắn đầu tiên và lưu vào biến 'msg'
    msg = await ctx.send("🔄 Đang đồng bộ lệnh, vui lòng đợi...")
    
    # Thực hiện đồng bộ
    synced_global = await bot.tree.sync()
    synced_guild = await bot.tree.sync(guild=ctx.guild)
    
    # 2. Chỉnh sửa (edit) chính tin nhắn đó thay vì gửi tin mới
    await msg.edit(content=f"✅ Đã đồng bộ **{len(synced_global)}** lệnh toàn cầu và **{len(synced_guild)}** lệnh server!")
    
    # 3. Tự xóa thông báo của bot sau 5 giây
    await msg.delete(delay=5.0)
    
    # 4. Tự xóa luôn cả tin nhắn gõ lệnh '!sync' của bạn (nếu bot có quyền)
    try:
        await ctx.message.delete(delay=5.0)
    except discord.Forbidden:
        pass # Bỏ qua nếu bot không có quyền quản lý tin nhắn

# Tải tất cả plugin trong thư mục plugins và các thư mục con
async def load_extensions():
    for root, dirs, files in os.walk('./plugins'):
        for filename in files:
            if filename.endswith('.py') and not filename.startswith('__'):
                # Chuyển đường dẫn file thành dạng module (vd: plugins.system.restart)
                path = os.path.relpath(os.path.join(root, filename), '.')
                module_name = path.replace(os.sep, '.')[:-3]
                
                await bot.load_extension(module_name)
                print(f'✅ Đã tải plugin: {module_name}')

async def main():
    async with bot:
        await load_extensions()
        await bot.start(TOKEN)

if __name__ == '__main__':
    import asyncio
    asyncio.run(main())