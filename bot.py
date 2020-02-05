import discord
import time
import asyncio
import datetime
import pytz
from discord.ext import commands
import os
from discord.utils import get
import youtube_dl

token = 'Njc0MzQ1NDg2MDY4NDgyMDUx.XjnUyA.UKpJP_i1g9kQGTzbB5jFDagoqRI'
client = commands.Bot(command_prefix = '!')
timechannel = 674348205948796958
memberchannel = 674348439856742430
guild = 569414055438319637
tz = pytz.timezone('Asia/Shanghai')

@client.event
async def on_ready():
    print('We have logged in as {0.user}'.format(client))
    while True:
        now = datetime.datetime.now(tz)
        times = "上午"
        hour = now.hour
        minute = now.minute
        if(hour >= 12):
            if hour != 12:
                hour -= 12
            times = "下午"
        await client.get_channel(timechannel).edit(name=f"台灣{times}{hour}時{minute}分 ") # The channel gets changed here
        await asyncio.sleep(10)
@client.event
async def on_member_join(member):
    id = client.get_guild(guild)
    for channel in member.guild.channels:
        if str(channel) == "join":
            await channel.send(f"""Welcome to the server {member.mention}""")
    await client.get_channel(memberchannel).edit(name=f"伺服器人數\t {id.member_count} ")

@client.command()
async def hello(ctx):
    await ctx.send("怎麼啦~主人?")
@client.command()
async def users(ctx):
    id = client.get_guild(guild)
    await ctx.send(f"""Num of Members : {id.member_count} """)
@client.command()
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
@client.command(pass_context=True, aliases=['l', 'lea'])
async def leave(ctx):
    channel = ctx.message.author.voice.channel
    voice = get(client.voice_clients, guild=ctx.guild)

    if voice and voice.is_connected():
        await voice.disconnect()
        print(f"The bot has left {channel}")
        await ctx.send(f"Left {channel}")
    else:
        print("Bot was told to leave voice channel, but was not in one")
        await ctx.send("Don't think I am in a voice channel")

@client.command(pass_context=True, aliases=['p', 'pla'])
async def play(ctx, url: str):
    discord.opus.load_opus('libopus.so')
    channel = ctx.message.author.voice.channel
    voice = get(client.voice_clients, guild=ctx.guild)

    if voice and voice.is_connected():
        await voice.move_to(channel)
    else:
        voice = await channel.connect()
        print(f"The bot has connected to {channel}\n")

    await ctx.send(f"Joined {channel}")

    song_there = os.path.isfile("song.mp3")
    try:
        if song_there:
            os.remove("song.mp3")
            print("Removed old song file")
    except PermissionError:
        print("Trying to delete song file, but it's being played")
        await ctx.send("ERROR: Music playing")
        return

    await ctx.send("正在準備音樂!")

    voice = get(client.voice_clients, guild=ctx.guild)

    ydl_opts = {
        'format': 'bestaudio/best',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
    }

    with youtube_dl.YoutubeDL(ydl_opts) as ydl:
        print("Downloading audio now\n")
        ydl.download([url])

    for file in os.listdir("./"):
        if file.endswith(".mp3"):
            name = file
            print(f"Renamed File: {file}\n")
            os.rename(file, "song.mp3")

    voice.play(discord.FFmpegPCMAudio("song.mp3"), after=lambda e: print("Song done!"))
    voice.source = discord.PCMVolumeTransformer(voice.source)
    voice.source.volume = 0.07

    nname = name.rsplit("-", 2)
    await ctx.send(f"Playing: {nname[0]}")
    print("playing\n")
client.run(token)
