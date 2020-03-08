import asyncio
import functools
import itertools
import math
import random
import pytz
import discord
import youtube_dl
from async_timeout import timeout
from discord.ext import commands,tasks
import time
import datetime
from itertools import cycle
from random import randint


token = 'Njc0MjgwNDk2MTQ2MTUzNTEy.XmSy_g.BbD2XH4YF1Jxyl95pfO_YBmrVys'
timechannel = 674348205948796958
memberchannel = 674348439856742430
guild = 569414055438319637
tz = pytz.timezone('Asia/Shanghai')


bot = commands.Bot('!', description='Yet another music bot.')


@bot.event
async def on_ready():
    print('We have logged in as {0.user}'.format(bot))
    change_status.start()
    while True:
        now = datetime.datetime.now(tz)
        times = "上午"
        hour = now.hour
        minute = now.minute
        if(hour >= 12 and hour < 18):
            if hour != 12:
                hour -= 12
            times = "下午"
        elif hour >= 18:
            if hour != 12:
                hour -= 12
            times = "晚上"
        await bot.get_channel(timechannel).edit(name=f"台灣{times}{hour}時{minute}分 ") # The channel gets changed here
        await asyncio.sleep(10)
@bot.event
async def on_member_join(member):
    id = bot.get_guild(guild)
    for channel in member.guild.channels:
        if str(channel) == "join":
            await channel.send(f"""{member.mention}お帰りなさいませ、ご主人様！""")
    await bot.get_channel(memberchannel).edit(name=f"伺服器人數\t {id.member_count} ")

@bot.command()
async def hello(ctx):
    await ctx.send("怎麼啦～主人？")
@bot.command()
async def users(ctx):
    id = bot.get_guild(guild)
    await ctx.send(f"""伺服器人數為 ： {id.member_count} 呦 """)
@bot.command()
async def confess(ctx):
    await ctx.send("我的心意還沒有傳達給你")
    time.sleep(2)
    await ctx.send("所以")
    time.sleep(2)
    await ctx.send("我希望")
    time.sleep(2)
    await ctx.send("你能多了解我一些")
    time.sleep(2)
    await ctx.send("我想要讓你知道")
    time.sleep(2)
    await ctx.send("我是有多麼喜歡你")
    time.sleep(2)
    await ctx.send("做好覺悟吧!")
    time.sleep(2)
    await ctx.send("主人<3")
    time.sleep(1)
    await ctx.send("https://imgur.com/EOPfIbh")

@bot.command()
async def calcdate(ctx, day: int):
	"""Add or subtract given day count by today and return."""
	td = datetime.datetime.now()
	today = datetime.date.today()
	tdelta = datetime.timedelta(days=day)
	result = today + tdelta
	dt = datetime.datetime.combine(result, td.time())
	embed = discord.Embed(timestamp=dt)
	await ctx.channel.send(embed=embed)


@bot.command(aliases=["ms"])
async def minesweeper(ctx, width: int = 10, height: int = 10, difficulty: int = 30):
    """Tired of moderation? Here is a mini minesweeper game for you!
    (PS: Don't show spoiler content to experience the fun!)
    """
    grid = tuple([['' for i in range(width)] for j in range(height)])
    num = ('0⃣', '1⃣', '2⃣', '3⃣', '4⃣', '5⃣', '6⃣', '7⃣', '8⃣')
    msg = ''

    if not (1 <= difficulty <= 100):
        await ctx.send("Please enter difficulty in terms of percentage (1-100).")
        return
    if width <= 0 or height <= 0:
        await ctx.send("Invalid width or height value.")
        return
    if width * height > 198:
        # 198 is the maximum number of emojis you can send in one Discord message.
        # It is however undocumented by Discord, we found the number via our own research.
        return await ctx.channel.send("Your grid size is too big.")
        return
    if width * height <= 4:
        await ctx.send("Your grid size is too small.")
        return

    # set bombs in random location
    for y in range(0, height):
        for x in range(0, width):
            if randint(0, 100) <= difficulty:
                grid[y][x] = '💣'

    # now set the number emojis
    for y in range(0, height):
        for x in range(0, width):
            if grid[y][x] != '💣':
                grid[y][x] = num[sum((
                    grid[y - 1][x - 1] == '💣' if y - 1 >= 0 and x - 1 >= 0 else False,
                    grid[y - 1][x] == '💣' if y - 1 >= 0 else False,
                    grid[y - 1][x + 1] == '💣' if y - 1 >= 0 and x + 1 < width else False,
                    grid[y][x - 1] == '💣' if x - 1 >= 0 else False,
                    grid[y][x + 1] == '💣' if x + 1 < width else False,
                    grid[y + 1][x - 1] == '💣' if y + 1 < height and x - 1 >= 0 else False,
                    grid[y + 1][x] == '💣' if y + 1 < height else False,
                    grid[y + 1][x + 1] == '💣' if y + 1 < height and x + 1 < width else False
                ))]
    await ctx.send(grid[y][x])

    # generate message
    for i in grid:
        for tile in i:
            msg += '||' + tile + '|| '
        msg += '\n'
    await ctx.send(msg)
@bot.command()
async def ping(ctx):
    await ctx.send(f"我回應主人的時間是{round(bot.latency*1000)} ms呦！")
status = cycle(['Do^3!','小提琴!','鋼琴!','書法!','長笛!','唱歌!','打扮!','綁蝴蝶結!','看著主人發呆!'])
@bot.command()
async def say(ctx,*,msg):
    await ctx.message.delete()
    await ctx.send(msg)
@bot.command()
async def clean(ctx,num:int):
    await ctx.channel.purge(limit=num+1)

@tasks.loop(seconds = 5)
async def change_status():
    await bot.change_presence(status=discord.Status.idle, activity=discord.Game(next(status)))

bot.run(token)