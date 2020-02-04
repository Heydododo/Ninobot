import discord
import time
import asyncio
import datetime
import pytz
from discord.ext import commands

messages = joined = 0


token = 'Njc0MzQ1NDg2MDY4NDgyMDUx.XjnUyA.UKpJP_i1g9kQGTzbB5jFDagoqRI'

client = commands.Bot(command_prefix = '!')
timechannel = 674348205948796958
memberchannel = 674348439856742430
tz = pytz.timezone('Asia/Shanghai')
'''async def update_stats():
    await client.wait_until_ready()
    global messages, joined

    while not client.is_closed():
        try:
            with open("stats.txt", "a") as f:
                f.write(f"Time: {int(time.time())}, Messages: {messages}, Members Joined: {joined}\n")

            messages = 0
            joined = 0

            await asyncio.sleep(60)
        except Exception as e:
            print(e)
            await asyncio.sleep(60)'''
@client.event
async def on_ready():
    print('We have logged in as {0.user}'.format(client))
    while True:
        now = datetime.datetime.now(tz)
        times = "上午"
        hour = now.hour
        minute = now.minute
        if(hour > 12):
            hour -= 12
            times = "下午"
        await client.get_channel(timechannel).edit(name=f"台灣{times}{hour}時{minute}分 ") # The channel gets changed here
        await asyncio.sleep(10)
@client.event
async def on_member_join(member):
    id = client.get_guild(569414055438319637)
    global joined
    joined += 1
    for channel in member.guild.channels:
        if str(channel) == "join":
            await channel.send(f"""Welcome to the server {member.mention}""")
    await client.get_channel(memberchannel).edit(name=f"伺服器人數\t {id.member_count} ")
@client.event
async def on_message(message):
    global messages
    messages += 1
    id = client.get_guild(569414055438319637)
    if message.content.find("!hello") != -1:
        await message.channel.send("怎麼啦~主人?")
    elif message.content == "!users":
        await message.channel.send(f"""# of Members: {id.member_count} """)
    elif message.content == "!confess":
        await message.channel.send("我的心意還沒有傳達給你")
        time.sleep(2)
        await message.channel.send("所以")
        time.sleep(2)
        await message.channel.send("我希望")
        time.sleep(2)
        await message.channel.send("你能多了解我一些")
        time.sleep(2)
        await message.channel.send("我想要讓你知道")
        time.sleep(2)
        await message.channel.send("我是有多麼喜歡你")
        time.sleep(2)
        await message.channel.send("做好覺悟吧!")
        time.sleep(2)
        await message.channel.send("主人<3")
        await message.channel.send(file=discord.File('nino.jpg'))
'''client.loop.create_task(update_stats())'''
client.run(token)
