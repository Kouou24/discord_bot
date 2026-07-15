import discord
from discord.ext import commands, tasks
import requests
import asyncio
from datetime import datetime
import pytz

# ========== 設定區 ==========
BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHANNEL_ID = int(os.environ.get("CHANNEL_ID"))

SEND_HOUR = 2        # 每天幾點發送（24小時制）
SEND_MINUTE = 13      # 幾分發送
TIMEZONE = "Asia/Taipei"

FRIENDS = [
    "noujiru",
    "dase",
    "haribobo",
    "moonwhite",
    "SSSLC",
    "XiaojieOuO"
]

API_URL = "https://lulumi-tools.com/data/v2/rankings.json"
# ============================

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)


# ========== 爬蟲 ==========

def format_exp(exp: int) -> str:
    return f"{exp / 1_000_000_000:.2f}B"


def fetch_and_find() -> list:
    """抓取 API 並找出朋友資料"""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    
    response = requests.get(API_URL, headers=headers, timeout=30)
    all_data = response.json()
    
    # 找出玩家 list
    player_list = None
    for key in all_data.keys():
        value = all_data[key]
        if isinstance(value, list) and len(value) > 0:
            player_list = value
            break
    
    if not player_list:
        raise Exception("找不到玩家資料")
    
    player_dict = {p['name'].lower(): p for p in player_list}
    
    found_players = []
    not_found = []
    
    for name in FRIENDS:
        player = player_dict.get(name.lower())
        if player:
            found_players.append(player)
        else:
            not_found.append(name)
    
    return found_players, not_found


# ========== 格式化訊息 ==========

def format_message(found_players: list, not_found: list) -> str:
    tz = pytz.timezone(TIMEZONE)
    now = datetime.now(tz)
    date_str = now.strftime("%Y/%m/%d")
    
    # 按今日經驗排序
    sorted_players = sorted(found_players, key=lambda x: x['dailyGain'], reverse=True)
    champion = sorted_players[0]
    
    lines = []
    lines.append(f"# 🍁 每日經驗排行榜")
    lines.append(f"📅 {date_str}")
    lines.append("```")
    lines.append(f"{'　':<2} {'名稱':<15} {'職業':<22} {'今日經驗':>10}")
    lines.append("─" * 55)
    
    for i, p in enumerate(sorted_players):
        lines.append(
            f" {p['name']:<15} {p['job']:<22} {format_exp(p['dailyGain']):>10}"
        )
    
    lines.append("```")
    lines.append(f"🏆 今日冠軍：**{champion['name']}** ({champion['job']} | Lv.{champion['level']})")
    lines.append(f"　 今日經驗：**{format_exp(champion['dailyGain'])}**")
    
    if not_found:
        lines.append(f"\n⚠️ 找不到以下角色：{', '.join(f'`{n}`' for n in not_found)}")
    
    lines.append(f"\n> 資料來源：lulumi-tools.com｜更新：{now.strftime('%H:%M')}")
    
    return "\n".join(lines)


# ========== 發送功能 ==========

async def send_ranking(channel):
    loading = await channel.send("⏳ 正在查詢每日經驗資料...")
    
    try:
        loop = asyncio.get_event_loop()
        found_players, not_found = await loop.run_in_executor(None, fetch_and_find)
        
        message = format_message(found_players, not_found)
        
        await loading.delete()
        await channel.send(message)
        print(f"✅ 排行榜已發送（{datetime.now()}）")
        
    except Exception as e:
        await loading.edit(content=f"❌ 發生錯誤：{e}")
        print(f"❌ 錯誤：{e}")


# ========== Bot 事件 ==========

@bot.event
async def on_ready():
    print(f"✅ Bot 已上線：{bot.user}")
    print(f"📌 每天 {SEND_HOUR:02d}:{SEND_MINUTE:02d} 發送排行榜")
    if not daily_ranking.is_running():
        daily_ranking.start()


# ========== 定時任務 ==========

@tasks.loop(minutes=1)
async def daily_ranking():
    tz = pytz.timezone(TIMEZONE)
    now = datetime.now(tz)
    
    if now.hour == SEND_HOUR and now.minute == SEND_MINUTE:
        channel = bot.get_channel(CHANNEL_ID)
        if channel:
            await send_ranking(channel)
        else:
            print(f"❌ 找不到頻道：{CHANNEL_ID}")


@daily_ranking.before_loop
async def before_daily_ranking():
    await bot.wait_until_ready()


# ========== 指令 ==========

@bot.command(name="排行")
async def manual_ranking(ctx):
    """!排行 — 手動觸發"""
    await send_ranking(ctx.channel)


@bot.command(name="測試")
async def test_command(ctx):
    """!測試 — 確認 Bot 狀態"""
    tz = pytz.timezone(TIMEZONE)
    now = datetime.now(tz)
    await ctx.send(
        f"✅ Bot 運作正常\n"
        f"🕐 目前時間：`{now.strftime('%Y/%m/%d %H:%M:%S')}`\n"
        f"⏰ 排行榜時間：每天 `{SEND_HOUR:02d}:{SEND_MINUTE:02d}`"
    )


# ========== 啟動 ==========
bot.run(BOT_TOKEN)