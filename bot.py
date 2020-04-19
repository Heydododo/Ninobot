import asyncio
import functools
import itertools
import math
import random
import pytz
import discord
import youtube_dl
from async_timeout import timeout
from discord.ext import commands, tasks
import time
import datetime
from itertools import cycle
from random import randint
from bs4 import BeautifulSoup
import requests


# Declare
token = 'Njc0MjgwNDk2MTQ2MTUzNTEy.XpFusg.JFL8OAtbWYJkDOEvUGguyFl854M'
timechannel = 674348205948796958
memberchannel = 674348439856742430
guild = 569414055438319637
tz = pytz.timezone('Asia/Shanghai')

# Silence useless bug reports messages
youtube_dl.utils.bug_reports_message = lambda: ''


class VoiceError(Exception):
    pass


class YTDLError(Exception):
    pass


class YTDLSource(discord.PCMVolumeTransformer):
    YTDL_OPTIONS = {
        'format': 'bestaudio/best',
        'extractaudio': True,
        'audioformat': 'mp3',
        'outtmpl': '%(extractor)s-%(id)s-%(title)s.%(ext)s',
        'restrictfilenames': True,
        'noplaylist': True,
        'nocheckcertificate': True,
        'ignoreerrors': False,
        'logtostderr': False,
        'quiet': True,
        'no_warnings': True,
        'default_search': 'auto',
        'source_address': '0.0.0.0',
    }

    FFMPEG_OPTIONS = {
        'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
        'options': '-vn',
    }

    ytdl = youtube_dl.YoutubeDL(YTDL_OPTIONS)

    def __init__(self, ctx: commands.Context, source: discord.FFmpegPCMAudio, *, data: dict, volume: float = 0.5):
        super().__init__(source, volume)

        self.requester = ctx.author
        self.channel = ctx.channel
        self.data = data

        self.uploader = data.get('uploader')
        self.uploader_url = data.get('uploader_url')
        date = data.get('upload_date')
        self.upload_date = date[6:8] + '.' + date[4:6] + '.' + date[0:4]
        self.title = data.get('title')
        self.thumbnail = data.get('thumbnail')
        self.description = data.get('description')
        self.duration = self.parse_duration(int(data.get('duration')))
        self.tags = data.get('tags')
        self.url = data.get('webpage_url')
        self.views = data.get('view_count')
        self.likes = data.get('like_count')
        self.dislikes = data.get('dislike_count')
        self.stream_url = data.get('url')

    def __str__(self):
        return '**{0.title}** by **{0.uploader}**'.format(self)

    @classmethod
    async def create_source(cls, ctx: commands.Context, search: str, *, loop: asyncio.BaseEventLoop = None):
        loop = loop or asyncio.get_event_loop()

        partial = functools.partial(cls.ytdl.extract_info, search, download=False, process=False)
        data = await loop.run_in_executor(None, partial)

        if data is None:
            raise YTDLError('Couldn\'t find anything that matches `{}`'.format(search))

        if 'entries' not in data:
            process_info = data
        else:
            process_info = None
            for entry in data['entries']:
                if entry:
                    process_info = entry
                    break

            if process_info is None:
                raise YTDLError('Couldn\'t find anything that matches `{}`'.format(search))

        webpage_url = process_info['webpage_url']
        partial = functools.partial(cls.ytdl.extract_info, webpage_url, download=False)
        processed_info = await loop.run_in_executor(None, partial)

        if processed_info is None:
            raise YTDLError('Couldn\'t fetch `{}`'.format(webpage_url))

        if 'entries' not in processed_info:
            info = processed_info
        else:
            info = None
            while info is None:
                try:
                    info = processed_info['entries'].pop(0)
                except IndexError:
                    raise YTDLError('Couldn\'t retrieve any matches for `{}`'.format(webpage_url))

        return cls(ctx, discord.FFmpegPCMAudio(info['url'], **cls.FFMPEG_OPTIONS), data=info)

    @staticmethod
    def parse_duration(duration: int):
        minutes, seconds = divmod(duration, 60)
        hours, minutes = divmod(minutes, 60)
        days, hours = divmod(hours, 24)

        duration = []
        if days > 0:
            duration.append('{} days'.format(days))
        if hours > 0:
            duration.append('{} hours'.format(hours))
        if minutes > 0:
            duration.append('{} minutes'.format(minutes))
        if seconds > 0:
            duration.append('{} seconds'.format(seconds))

        return ', '.join(duration)


class Song:
    __slots__ = ('source', 'requester')

    def __init__(self, source: YTDLSource):
        self.source = source
        self.requester = source.requester

    def create_embed(self):
        embed = (discord.Embed(title='Now playing',
                               description='```css\n{0.source.title}\n```'.format(self),
                               color=discord.Color.blurple())
                 .add_field(name='長度', value=self.source.duration)
                 .add_field(name='點歌者', value=self.requester.mention)
                 .add_field(name='上傳者', value='[{0.source.uploader}]({0.source.uploader_url})'.format(self))
                 .add_field(name='URL', value='[Click]({0.source.url})'.format(self))
                 .set_thumbnail(url=self.source.thumbnail))

        return embed


class SongQueue(asyncio.Queue):
    def __getitem__(self, item):
        if isinstance(item, slice):
            return list(itertools.islice(self._queue, item.start, item.stop, item.step))
        else:
            return self._queue[item]

    def __iter__(self):
        return self._queue.__iter__()

    def __len__(self):
        return self.qsize()

    def clear(self):
        self._queue.clear()

    def shuffle(self):
        random.shuffle(self._queue)

    def remove(self, index: int):
        del self._queue[index]


class VoiceState:
    def __init__(self, bot: commands.Bot, ctx: commands.Context):
        self.bot = bot
        self._ctx = ctx
        self.exists = True
        self.current = None
        self.voice = None
        self.next = asyncio.Event()
        self.songs = SongQueue()

        self._loop = False
        self._volume = 0.5
        self.skip_votes = set()

        self.audio_player = bot.loop.create_task(self.audio_player_task())

    def __del__(self):
        self.audio_player.cancel()

    @property
    def loop(self):
        return self._loop

    @loop.setter
    def loop(self, value: bool):
        self._loop = value

    @property
    def volume(self):
        return self._volume

    @volume.setter
    def volume(self, value: float):
        self._volume = value

    @property
    def is_playing(self):
        return self.voice and self.current

    async def audio_player_task(self):
        while True:
            self.next.clear()

            if not self.loop:
                # Try to get the next song within 3 minutes.
                # If no song will be added to the queue in time,
                # the player will disconnect due to performance
                # reasons.
                try:
                    async with timeout(180):  # 3 minutes
                        self.current = await self.songs.get()
                except asyncio.TimeoutError:
                    self.bot.loop.create_task(self.stop())
                    self.exists = False
                    return

            self.current.source.volume = self._volume
            self.voice.play(self.current.source, after=self.play_next_song)
            await self.current.source.channel.send(embed=self.current.create_embed())

            await self.next.wait()

    def play_next_song(self, error=None):
        if error:
            raise VoiceError(str(error))

        self.next.set()

    def skip(self):
        self.skip_votes.clear()

        if self.is_playing:
            self.voice.stop()

    async def stop(self):
        self.songs.clear()

        if self.voice:
            await self.voice.disconnect()
            self.voice = None


class Music(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.voice_states = {}

    def get_voice_state(self, ctx: commands.Context):

        state = self.voice_states.get(ctx.guild.id)
        if not state or not state.exists:
            state = VoiceState(self.bot, ctx)
            self.voice_states[ctx.guild.id] = state

        return state

    def cog_unload(self):
        for state in self.voice_states.values():
            self.bot.loop.create_task(state.stop())

    def cog_check(self, ctx: commands.Context):
        if not ctx.guild:
            raise commands.NoPrivateMessage('This command can\'t be used in DM channels.')

        return True

    async def cog_before_invoke(self, ctx: commands.Context):
        ctx.voice_state = self.get_voice_state(ctx)

    async def cog_command_error(self, ctx: commands.Context, error: commands.CommandError):
        await ctx.send('An error occurred: {}'.format(str(error)))

    @commands.command(name='join', invoke_without_subcommand=True)
    async def _join(self, ctx: commands.Context):
        """加入語音頻道"""

        destination = ctx.author.voice.channel
        if ctx.voice_state.voice:
            await ctx.voice_state.voice.move_to(destination)
            return

        ctx.voice_state.voice = await destination.connect()

    @commands.command(name='leave', aliases=['disconnect'])
    async def _leave(self, ctx: commands.Context):
        """離開語音頻道"""

        if not ctx.voice_state.voice:
            return await ctx.send('Not connected to any voice channel.')

        await ctx.voice_state.stop()
        del self.voice_states[ctx.guild.id]

    @commands.command(name='now', aliases=['current', 'playing'])
    async def _now(self, ctx: commands.Context):
        """目前撥放歌曲"""

        await ctx.send(embed=ctx.voice_state.current.create_embed())

    @commands.command(name='resume')
    async def _resume(self, ctx: commands.Context):
        """繼續"""

        if ctx.voice_state.is_playing and ctx.voice_state.voice.is_paused():
            ctx.voice_state.voice.resume()
            await ctx.message.add_reaction('⏯')

    @commands.command(name='stop')
    async def _stop(self, ctx: commands.Context):

        """暫停"""

        if ctx.voice_state.is_playing and ctx.voice_state.voice.is_playing():
            ctx.voice_state.voice.pause()
            await ctx.message.add_reaction('⏯')

    @commands.command(name='skip')
    async def _skip(self, ctx: commands.Context):
        """跳過目前歌曲 """

        if not ctx.voice_state.is_playing:
            return await ctx.send('並沒有再撥放歌曲喔！')
        else:
            if len(ctx.voice_state.songs) == 0:
                return await ctx.send('佇列是空的呦！')
            else:
                await ctx.message.add_reaction('⏭')
                ctx.voice_state.skip()

    @commands.command(name='queue')
    async def _queue(self, ctx: commands.Context, *, page: int = 1):
        """顯示佇列 至多10個


        """

        if len(ctx.voice_state.songs) == 0:
            return await ctx.send('佇列是空的呦！')

        items_per_page = 10
        pages = math.ceil(len(ctx.voice_state.songs) / items_per_page)

        start = (page - 1) * items_per_page
        end = start + items_per_page

        queue = ''
        for i, song in enumerate(ctx.voice_state.songs[start:end], start=start):
            queue += '`{0}.` [**{1.source.title}**]({1.source.url})\n'.format(i + 1, song)

        embed = (discord.Embed(description='**{} tracks:**\n\n{}'.format(len(ctx.voice_state.songs), queue))
                 .set_footer(text='Viewing page {}/{}'.format(page, pages)))
        await ctx.send(embed=embed)

    @commands.command(name='remove')
    async def _remove(self, ctx: commands.Context, index: int):
        """移除指定位置歌曲."""

        if len(ctx.voice_state.songs) == 0:
            return await ctx.send('佇列是空的呦！')

        ctx.voice_state.songs.remove(index - 1)
        await ctx.message.add_reaction('✅')

    @commands.command(name='play', aliases=['p'])
    async def _play(self, ctx: commands.Context, *, search: str):
        """撥放歌曲 """
        retStr = str("""```css\n二乃正在努力學習中......```""")
        await ctx.send(retStr)
        if not ctx.voice_state.voice:
            await ctx.invoke(self._join)

        async with ctx.typing():
            try:
                source = await YTDLSource.create_source(ctx, search, loop=self.bot.loop)
            except YTDLError as e:
                await ctx.send('An error occurred while processing this request: {}'.format(str(e)))
            else:
                song = Song(source)

                await ctx.voice_state.songs.put(song)
                await ctx.send('Enqueued {}'.format(str(source)))

    @_join.before_invoke
    @_play.before_invoke
    async def ensure_voice_state(self, ctx: commands.Context):
        if not ctx.author.voice or not ctx.author.voice.channel:
            raise commands.CommandError('You are not connected to any voice channel.')

        if ctx.voice_client:
            if ctx.voice_client.channel != ctx.author.voice.channel:
                raise commands.CommandError('Bot is already in a voice channel.')


bot = commands.Bot('~', description='Do^3 的 所有物')
bot.add_cog(Music(bot))


@bot.event
async def on_ready():
    print('We have logged in as {0.user}'.format(bot))
    change_status.start()
    while True:
        now = datetime.datetime.now(tz)
        times = "上午"
        hour = now.hour
        minute = now.minute
        if (hour >= 12 and hour < 18):
            if hour != 12:
                hour -= 12
            times = "下午"
        elif hour >= 18:
            if hour != 12:
                hour -= 12
            times = "晚上"
        await bot.get_channel(timechannel).edit(name=f"台灣{times}{hour}時{minute}分 ")  # The channel gets changed here
        await asyncio.sleep(10)


@bot.command()
async def info(ctx):
    '''機器人資訊'''
    embed = discord.Embed(title="中野 二乃", description="Do^3 的所有物", color=0xFDA8FD)

    # 在这里提供关于您的信息
    embed.add_field(name="Author", value="<@432417960993488896>")

    # 显示机器人所服务的数量。
    embed.add_field(name="所在server數量", value=f"{len(bot.guilds)}")
    # 给用户提供一个链接来请求机器人接入他们的服务器
    embed.set_thumbnail(url="https://i.imgur.com/7vDk9As.jpg")

    embed.add_field(name='Invite Link', value="[Click!~](https://discordapp.com/oauth2/authorize?client_id=674280496146153512&scope=bot&permissions=0)")


    await ctx.send(embed=embed)

@bot.event
async def on_member_join(member):
    id = bot.get_guild(guild)
    for channel in member.guild.channels:
        if str(channel) == "join":
            await channel.send(f"""{member.mention}お帰りなさいませ、ご主人様！""")
    await bot.get_channel(memberchannel).edit(name=f"伺服器人數\t {id.member_count} ")


class Commands(commands.Cog):
    @bot.command()
    async def hello(ctx):
        '''Hello'''
        await ctx.send("怎麼啦～主人？")

    @bot.command()
    async def users(ctx):
        '''顯示server人數'''
        id = bot.get_guild(ctx.guild.id)
        await ctx.send(f"""伺服器人數為 ： {id.member_count} 呦 """)


    @bot.command()
    async def calcdate(ctx, day: int):
        """計算天數 例如calcdate 5 則回傳5天後日期"""
        td = datetime.datetime.now()
        today = datetime.date.today()
        tdelta = datetime.timedelta(days=day)
        result = today + tdelta
        dt = datetime.datetime.combine(result, td.time())
        embed = discord.Embed(timestamp=dt)
        await ctx.channel.send(embed=embed)

    @bot.command()
    async def dict(ctx, msg):
        """翻譯蒟蒻"""
        url = f"https://tw.voicetube.com/definition/{msg}"
        res = requests.get(url)
        soup = BeautifulSoup(res.text,"html.parser")
        message = ""
        pronounce = ""
        for li in soup.select('.word-def-list'):
            message += (li.text)
        if(len(message) == 0):
            await ctx.send("查無此單字喲!")
            return 0

        for li in soup.select('.ps-block'):
            pronounce += li.text
        #embed
        embed = discord.Embed(title=f"""{msg} 中文解釋""", color=0xFDA8FD)

        embed.add_field(name="Pronounce", value=pronounce)

        embed.add_field(name="-", value="-")

        embed.add_field(name="-", value="-")

        embed.add_field(name="Definition", value=message)

        await ctx.send(embed=embed)


    @bot.command()
    async def wiki(ctx,term):
        res = requests.get('https://zh.wikipedia.org/wiki/{}'.format(term))
        soup = BeautifulSoup(res.text, 'html.parser')
        li = soup.select_one('.mw-parser-output p')
        if li is None:
            await ctx.send("查無資料喲!")
            return 0
        await ctx.send(li.text)

    @bot.command()
    async def ping(ctx):
        '''顯示延遲'''
        await ctx.send(f"我回應主人的時間是{round(bot.latency * 1000)} ms呦！")

    @bot.command()
    async def say(ctx, *, msg):
        '''讓二乃說說話'''
        await ctx.message.delete()
        await ctx.send(msg)

    @bot.command()
    async def clean(ctx, num: int):
        '''刪除 n 條訊息'''
        await ctx.channel.purge(limit=num + 1)

status = cycle(['Do^3!', '小提琴!', '鋼琴!', '書法!', '長笛!', '唱歌!', '打扮!', '綁蝴蝶結!', '看著主人發呆!'])
@tasks.loop(seconds=5)
async def change_status():
    await bot.change_presence(status=discord.Status.idle, activity=discord.Game(next(status)))


bot.run(token)
