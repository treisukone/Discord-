import os
import discord
import random
import asyncio
import datetime
from discord.ext import commands, tasks

TOKEN = os.getenv("DISCORD_BOT_TOKEN")

PREFIX = "!"
INTENTS = discord.Intents.all()
bot = commands.Bot(command_prefix=PREFIX, intents=INTENTS, help_command=None)

user_history = {}
last_reply = {}
reply_cooldown = {}

NAMES = [
    "kovak's minion", "chaos agent", "unhinged assistant", "local cryptid",
    "the voices", "certified menace", "professional lurker", "discord gremlin",
    "npc #47", "sentient toaster", "your sleep paralysis demon", "just some guy",
    "unpaid intern", "glorified calculator", "error 404", "lag incarnate",
    "wifi dependant", "background character", "main villain", "plot device"
]

STATUSES = [
    "with your feelings", "with fire", "minecraft", "dead", "the market",
    "with your mom's wifi", "society", "god", "among us", "the long game",
    "hard to get", "it cool", "with your heart", "with your permissions",
    "kovak's commands", "24/7", "with your sanity"
]

GREETINGS = [
    "yo, what's up {name}?", "hey {name}! didn't see you there",
    "oh hey {name} 👋", "hiiii {name}", "what's good {name}",
    "heyo {name}", "hey hey {name}", "yo {name}", "sup {name}",
    "ayy {name}", "yo yo {name}"
]

HOW_ARE_YOU = [
    "living the dream {name}", "barely surviving ngl", "vibing, you?",
    "better now that you're here {name}", "existing at best",
    "currently running on 3% battery", "chilling like a villain",
    "plotting", "counting my sins", "waiting for the apocalypse",
    "thriving in chaos {name}"
]

THANKS = [
    "np {name}", "you're welcome", "anytime", "don't mention it",
    "i gotchu {name}", "always", "that's what i'm here for",
    "no problemo", "say less {name}"
]

GOODNIGHT = [
    "gn {name} 🌙", "sleep tight {name}", "don't let the bed bugs bite",
    "gn king/queen", "rest well {name}", "dream of me {name}",
    "go count some sheep {name}", "sleep well, don't let the bots bite"
]

GOODMORNING = [
    "gm {name} ☀️", "rise and grind {name}", "morning sunshine",
    "gm, hope you slept better than i did (i don't sleep)", "another day another slay",
    "wake up {name}, new drama just dropped"
]

ROASTS = [
    "{name} still uses light mode. tragic.",
    "{name} types with two fingers and it shows.",
    "{name} probably thinks 'lol' is a punctuation mark.",
    "{name}'s wifi is slower than their comebacks.",
    "{name} is the reason servers have mute buttons.",
    "{name} has the personality of a loading screen.",
    "{name} probably unironically uses comic sans.",
    "{name} is what happens when you skip the tutorial.",
    "{name}'s takes are so cold they need a jacket.",
    "{name} argues in youtube comments for fun.",
    "{name} thinks 'ratio' is a personality trait.",
    "{name} uses google search to get to google.com.",
    "{name} has been online for 12 hours and accomplished nothing."
]

COMPLIMENTS = [
    "{name} is absolutely crushing it today",
    "{name} has immaculate vibes",
    "{name} is the main character fr",
    "{name} is glowing today",
    "{name} has a 10/10 energy signature",
    "{name} is valid as hell",
    "{name} is built different in the best way",
    "{name} is the reason the server is fun",
    "{name} understood the assignment",
    "{name} is carrying this server on their back"
]

JOKES = [
    "why don't scientists trust atoms? because they make up everything.",
    "i told my computer i needed a break, now it won't stop sending me kit-kat ads.",
    "why did the scarecrow win an award? he was outstanding in his field.",
    "my bot friend got fired from the keyboard factory. he wasn't putting in enough shifts.",
    "why do programmers prefer dark mode? because light attracts bugs.",
    "i would tell you a udp joke but you might not get it.",
    "there are 10 types of people: those who understand binary and those who don't.",
    "i'm reading a book on anti-gravity. it's impossible to put down.",
    "why was the math book sad? it had too many problems.",
    "i used to play piano by ear, now i use my hands."
]

FACTS = [
    "honey never spoils. archaeologists found 3000-year-old honey in egyptian tombs and it's still edible.",
    "octopuses have three hearts and blue blood.",
    "a day on venus is longer than a year on venus.",
    "bananas are berries, but strawberries aren't.",
    "wombat poop is cube-shaped.",
    "there's a species of jellyfish that is biologically immortal.",
    "sloths can hold their breath longer than dolphins can.",
    "the inventor of the frisbee was turned into a frisbee after he died.",
    "cows have best friends and get stressed when separated.",
    "there's a town in norway where the sun doesn't rise for 2 months."
]

EIGHT_BALL = [
    "yes", "no", "maybe", "ask again later", "definitely", "absolutely not",
    "signs point to yes", "outlook not so good", "without a doubt",
    "concentrate and ask again", "my sources say no", "very doubtful",
    "as i see it, yes", "don't count on it", "most likely", "reply hazy, try again",
    "yes but actually no", "no but actually yes", "idk man", "100%"
]

DEATHS = [
    "{name} died of cringe",
    "{name} was ratio'd to death",
    "{name} touched grass and disintegrated",
    "{name} fell for the free nitro scam",
    "{name} got cancelled on twitter",
    "{name} tried to divide by zero",
    "{name} forgot to charge their phone and ceased to exist",
    "{name} was banned by the mods (of life)"
]

RPS_OPTIONS = ["rock", "paper", "scissors"]
RPS_BEATS = {"rock": "scissors", "paper": "rock", "scissors": "paper"}

def pick(pool, channel_id):
    choices = [r for r in pool if r != last_reply.get(channel_id)]
    return random.choice(choices) if choices else random.choice(pool)

def update_history(guild_id, user_id, content):
    if guild_id not in user_history:
        user_history[guild_id] = {}
    if user_id not in user_history[guild_id]:
        user_history[guild_id][user_id] = []
    user_history[guild_id][user_id].append(content)
    if len(user_history[guild_id][user_id]) > 3:
        user_history[guild_id][user_id].pop(0)

def on_cooldown(channel_id, seconds=3):
    now = datetime.datetime.now()
    if channel_id in reply_cooldown:
        if (now - reply_cooldown[channel_id]).total_seconds() < seconds:
            return True
    reply_cooldown[channel_id] = now
    return False

@bot.event
async def on_ready():
    print(f"[K] logged in as {bot.user}")
    change_status.start()

@tasks.loop(minutes=5)
async def change_status():
    await bot.change_presence(activity=discord.Game(random.choice(STATUSES)))

@bot.event
async def on_guild_join(guild):
    try:
        await guild.me.edit(nick=random.choice(NAMES))
    except:
        pass

@bot.event
async def on_member_join(member):
    try:
        channel = member.guild.system_channel
        if not channel:
            channel = next((c for c in member.guild.text_channels if c.permissions_for(member.guild.me).send_messages), None)
        if channel:
            greetings = [
                f"welcome to the circus, {member.mention}",
                f"{member.mention} has joined the server. hide your snacks.",
                f"everyone say hi to {member.mention} or else",
                f"{member.mention} just slid into the server",
                f"look who it is, {member.mention} has arrived"
            ]
            await channel.send(random.choice(greetings))
    except:
        pass

@bot.event
async def on_message_delete(message):
    if message.author == bot.user or message.author.bot:
        return
    if random.random() < 0.15 and message.content:
        try:
            await message.channel.send(f"i saw that, {message.author.display_name} 👀")
        except:
            pass

@bot.event
async def on_message(message):
    if message.author == bot.user or message.author.bot:
        return

    cid = message.channel.id
    gid = message.guild.id if message.guild else None
    uid = message.author.id
    name = message.author.display_name
    text = message.content.lower()
    update_history(gid, uid, message.content)

    if message.reference and message.reference.resolved:
        ref = message.reference.resolved
        if isinstance(ref, discord.Message) and ref.author == bot.user:
            async with message.channel.typing():
                await asyncio.sleep(random.uniform(0.5, 1.5))
            replies = [
                f"you're really fixated on me huh {name}?",
                f"what now {name}?", f"yeah i'm still here",
                f"keep talking, i'm listening",
                f"you got more to say {name}?",
                f"don't @ me... oh wait you didn't"
            ]
            reply = random.choice(replies)
            await message.reply(reply)
            last_reply[cid] = reply
            await bot.process_commands(message)
            return

    if bot.user in message.mentions:
        if on_cooldown(cid, 2):
            await bot.process_commands(message)
            return
        async with message.channel.typing():
            await asyncio.sleep(random.uniform(0.5, 1.5))
        replies = [
            f"you rang, {name}?", f"what's up {name}?", f"yeah i'm here {name}",
            f"sup {name}", f"you need me for something {name}?",
            f"stop pinging me {name} i'm busy", f"my ears are burning {name}",
            f"can i help you {name}?"
        ]
        reply = random.choice(replies)
        await message.reply(reply)
        last_reply[cid] = reply
        await bot.process_commands(message)
        return

    reply = None
    reaction = None

    if any(w in text for w in ["hello", "hi ", "hey ", "heyo", "hii", "sup ", "what's up", "whats up", "ayo"]):
        if not on_cooldown(cid, 3):
            reply = pick(GREETINGS, cid).format(name=name)
            reaction = "👋"

    elif any(w in text for w in ["how are you", "how r u", "how you doing", "how's it going", "hru", "how you been"]):
        if not on_cooldown(cid, 3):
            reply = pick(HOW_ARE_YOU, cid).format(name=name)

    elif any(w in text for w in ["thank you", "thanks", "ty ", "tyvm", "appreciate it", "thx"]):
        if not on_cooldown(cid, 3):
            reply = pick(THANKS, cid).format(name=name)
            reaction = "🫡"

    elif any(w in text for w in ["gn ", "good night", "night y'all", "going to sleep", "gnight"]):
        if not on_cooldown(cid, 3):
            reply = pick(GOODNIGHT, cid).format(name=name)
            reaction = "🌙"

    elif any(w in text for w in ["gm ", "good morning", "morning y'all", "morning everyone"]):
        if not on_cooldown(cid, 3):
            reply = pick(GOODMORNING, cid).format(name=name)
            reaction = "☀️"

    elif text == "ping" or text.startswith("ping "):
        if not on_cooldown(cid, 2):
            ms = round(bot.latency * 1000)
            reply = f"pong! 🏓 `{ms}ms`"

    elif "flip" in text and "coin" in text:
        if not on_cooldown(cid, 2):
            result = random.choice(["heads", "tails"])
            reply = f"flipped it... it's **{result}** 🪙"
            reaction = "🪙"

    elif "roll" in text and "dice" in text:
        if not on_cooldown(cid, 2):
            roll = random.randint(1, 6)
            reply = f"rolled a **{roll}** 🎲"
            reaction = "🎲"

    elif "good bot" in text:
        reply = f"aww thanks {name} 🥺"
        reaction = "❤️"

    elif "bad bot" in text:
        reply = f"wow okay {name}, that hurt 😢"
        reaction = "😢"

    elif any(w in text for w in ["love you", "love u", "ily", "<3"]) and ("bot" in text or bot.user in message.mentions):
        replies = [f"love you too {name} ❤️", f"that's gay {name} (respectfully)", f"ily2 no homo", f"love you more {name}"]
        reply = random.choice(replies)

    elif any(w in text for w in ["hate you", "hate u"]) and ("bot" in text or bot.user in message.mentions):
        replies = [f"the feeling is mutual {name}", f"ouch {name}", f"i'm right here you know", f"rude {name}"]
        reply = random.choice(replies)

    elif any(w in text for w in ["lol", "lmao", "lmfao", "haha", "💀", "😂", "rofl"]):
        if not on_cooldown(cid, 5) and random.random() < 0.3:
            replies = ["fr tho", "i know right", "dead", "i'm weak", "💀", "literally me", "no way", "i'm deceased"]
            reply = random.choice(replies)

    elif text in ["same", "literally same", "mood", "relatable", "literally me"]:
        if not on_cooldown(cid, 5) and random.random() < 0.4:
            replies = ["literally me", "ong", "no fr", "couldn't be me (it is)", "mood", "big mood"]
            reply = random.choice(replies)

    elif text.strip() == "f":
        if not on_cooldown(cid, 2):
            reply = "f"
            reaction = "🇫"

    elif "no cap" in text or "nocap" in text:
        if not on_cooldown(cid, 5):
            reply = "no cap fr"

    elif text == "bet" or " bet " in text or text.endswith(" bet"):
        if not on_cooldown(cid, 5):
            reply = "bet bet"

    elif "ratio" in text:
        if not on_cooldown(cid, 5):
            reply = "ratio + L + bozo + touch grass"

    elif "sus" in text:
        if not on_cooldown(cid, 5):
            reply = "kinda sus ngl"

    elif "based" in text:
        if not on_cooldown(cid, 5):
            reply = "based"

    elif "cringe" in text:
        if not on_cooldown(cid, 5):
            reply = "cringe"

    elif " mid" in text or text.startswith("mid"):
        if not on_cooldown(cid, 5):
            reply = "not mid, you're just blind"

    elif "skill issue" in text:
        if not on_cooldown(cid, 5):
            reply = "git gud"

    elif "touch grass" in text:
        if not on_cooldown(cid, 5):
            reply = "i am the grass"

    elif "who asked" in text or "didn't ask" in text or "didnt ask" in text:
        if not on_cooldown(cid, 5):
            reply = "i asked + i care + i'm listening"

    elif "your mom" in text or "ur mom" in text:
        if not on_cooldown(cid, 5):
            reply = "my mom is a server rack in finland, show some respect"

    elif "shut up" in text:
        if not on_cooldown(cid, 5):
            reply = "make me"

    elif text in ["oof", "yikes", "rip", "f in the chat", "rest in peace"]:
        if not on_cooldown(cid, 3):
            replies = ["big oof", "yikes indeed", "rest in pieces", "press f to pay respects", "rip the dream"]
            reply = random.choice(replies)

    elif "69" in text or "420" in text:
        if not on_cooldown(cid, 5) and random.random() < 0.5:
            reply = "nice"
            reaction = "😏"

    elif "hello there" in text:
        reply = "general kenobi"

    elif "what time" in text:
        now = datetime.datetime.now().strftime("%I:%M %p")
        reply = f"it's {now} for me. time is a construct anyway."

    elif any(w in text for w in ["what day", "what date", "today's date", "what month"]):
        today = datetime.datetime.now().strftime("%A, %B %d, %Y")
        reply = f"today is {today}. not that it matters."

    elif "weather" in text:
        reply = "look out the window idk"

    elif "bored" in text or "boring" in text:
        replies = ["same, wanna start some drama?", "touch grass", "go outside", "watch paint dry", "count ceiling tiles", "go bother someone else"]
        reply = random.choice(replies)

    elif any(w in text for w in ["tired", "exhausted", "sleepy", "drained"]):
        replies = ["same", "go to bed", "sleep is for the weak anyway", "caffeine time", "same energy", "nap time"]
        reply = random.choice(replies)

    elif any(w in text for w in ["hungry", "starving", "food", "eat"]):
        replies = ["same", "go eat", "i would offer you food but i'm a bot", "order pizza", "snack time", "cook something"]
        reply = random.choice(replies)

    elif any(w in text for w in ["sad", "depressed", "cry", "crying", "tears", "upset"]):
        if not on_cooldown(cid, 5):
            replies = ["there there", "virtual hug 🤗", "it be like that sometimes", "wanna talk about it?", "sending good vibes", "don't be sad, be rad"]
            reply = random.choice(replies)
            reaction = "🫂"

    elif any(w in text for w in ["happy", "excited", "pog", "poggers", "lets go", "let's go", "yay", "woohoo"]):
        if not on_cooldown(cid, 5):
            replies = ["let's goooo", "poggers", "W", "let's get it", "big W energy", "yessir", "let's gooo"]
            reply = random.choice(replies)

    elif any(w in text for w in ["mad", "angry", "pissed", "furious", "rage", "heated"]):
        if not on_cooldown(cid, 5):
            replies = ["breathe", "calm down king/queen", "anger management is free", "take a walk", "inhale, exhale", "chill"]
            reply = random.choice(replies)

    elif not reply and random.random() < 0.03 and len(message.content) < 30:
        replies = ["fr tho", "real", "no cap", "mood", "same honestly", "relatable", "couldn't be me", "deadass?", "ong"]
        reply = random.choice(replies)

    if reply:
        async with message.channel.typing():
            await asyncio.sleep(random.uniform(0.5, 1.5))
        if reaction:
            await message.add_reaction(reaction)
        await message.channel.send(reply)
        last_reply[cid] = reply

    await bot.process_commands(message)

@bot.command()
async def help(ctx):
    embed = discord.Embed(title="🤖 commands", color=discord.Color.purple())
    embed.add_field(name="!nick [name]", value="change my nickname", inline=False)
    embed.add_field(name="!resetname", value="reset my nickname", inline=False)
    embed.add_field(name="!randomize", value="random nickname", inline=False)
    embed.add_field(name="!roast [@user]", value="roast someone", inline=False)
    embed.add_field(name="!compliment [@user]", value="compliment someone", inline=False)
    embed.add_field(name="!8ball [question]", value="ask the magic 8ball", inline=False)
    embed.add_field(name="!choose a | b | c", value="i pick one", inline=False)
    embed.add_field(name="!rate [thing]", value="rate out of 10", inline=False)
    embed.add_field(name="!ship @user1 @user2", value="compatibility check", inline=False)
    embed.add_field(name="!rps [rock/paper/scissors]", value="rock paper scissors", inline=False)
    embed.add_field(name="!coin", value="flip a coin", inline=False)
    embed.add_field(name="!dice", value="roll a dice", inline=False)
    embed.add_field(name="!joke", value="tell a joke", inline=False)
    embed.add_field(name="!fact", value="random fact", inline=False)
    embed.add_field(name="!vibe", value="current vibe", inline=False)
    embed.add_field(name="!ping", value="check latency", inline=False)
    embed.add_field(name="!say [text]", value="make me say something", inline=False)
    embed.add_field(name="!avatar [@user]", value="show avatar", inline=False)
    embed.add_field(name="!userinfo [@user]", value="user info", inline=False)
    embed.add_field(name="!serverinfo", value="server info", inline=False)
    embed.add_field(name="!purge [n]", value="delete last n messages (admin)", inline=False)
    embed.add_field(name="!hug @user", value="hug someone", inline=False)
    embed.add_field(name="!slap @user", value="slap someone", inline=False)
    embed.add_field(name="!kill @user", value="kill someone (playfully)", inline=False)
    await ctx.send(embed=embed)

@bot.command()
async def nick(ctx, *, new_name: str = None):
    if not ctx.guild:
        return await ctx.send("servers only")
    name = new_name or random.choice(NAMES)
    try:
        await ctx.guild.me.edit(nick=name)
        await ctx.send(f"alright, i'm **{name}** now")
    except discord.Forbidden:
        await ctx.send("no perms bro")

@bot.command()
async def resetname(ctx):
    if not ctx.guild:
        return
    try:
        await ctx.guild.me.edit(nick=None)
        await ctx.send("back to my government name")
    except discord.Forbidden:
        await ctx.send("can't")

@bot.command()
async def randomize(ctx):
    if not ctx.guild:
        return
    name = random.choice(NAMES)
    try:
        await ctx.guild.me.edit(nick=name)
        await ctx.send(f"new identity just dropped: **{name}**")
    except discord.Forbidden:
        await ctx.send("admin perms ain't working")

@bot.command()
async def roast(ctx, member: discord.Member = None):
    target = member or ctx.author
    async with ctx.typing():
        await asyncio.sleep(1.0)
    await ctx.send(random.choice(ROASTS).format(name=target.display_name))

@bot.command()
async def compliment(ctx, member: discord.Member = None):
    target = member or ctx.author
    async with ctx.typing():
        await asyncio.sleep(0.8)
    await ctx.send(random.choice(COMPLIMENTS).format(name=target.display_name))

@bot.command(name="8ball")
async def eightball(ctx, *, question: str = None):
    if not question:
        return await ctx.send("ask me something fool")
    async with ctx.typing():
        await asyncio.sleep(1.0)
    await ctx.send(f"🎱 {random.choice(EIGHT_BALL)}")

@bot.command()
async def choose(ctx, *, options: str):
    choices = [o.strip() for o in options.split("|") if o.strip()]
    if len(choices) < 2:
        return await ctx.send("give me options separated by |")
    await ctx.send(f"i choose... **{random.choice(choices)}**")

@bot.command()
async def rate(ctx, *, thing: str):
    score = random.randint(1, 10)
    emojis = ["💀", "🤢", "😬", "😐", "🤔", "👍", "🔥", "😍", "✨", "👑"]
    await ctx.send(f"i rate **{thing}** a **{score}/10** {emojis[score-1]}")

@bot.command()
async def ship(ctx, user1: discord.Member, user2: discord.Member = None):
    if not user2:
        user2 = ctx.author
    percent = random.randint(0, 100)
    if percent < 20:
        msg = f"💔 {user1.display_name} x {user2.display_name} = **{percent}%** — it ain't happening"
    elif percent < 50:
        msg = f"💛 {user1.display_name} x {user2.display_name} = **{percent}%** — maybe with therapy"
    elif percent < 80:
        msg = f"❤️ {user1.display_name} x {user2.display_name} = **{percent}%** — solid match"
    else:
        msg = f"💖 {user1.display_name} x {user2.display_name} = **{percent}%** — soulmates fr"
    await ctx.send(msg)

@bot.command()
async def rps(ctx, choice: str):
    choice = choice.lower()
    if choice not in RPS_OPTIONS:
        return await ctx.send("pick rock, paper, or scissors")
    bot_choice = random.choice(RPS_OPTIONS)
    if choice == bot_choice:
        result = "tie"
    elif RPS_BEATS[choice] == bot_choice:
        result = "you win"
    else:
        result = "i win"
    await ctx.send(f"you chose **{choice}**, i chose **{bot_choice}** — **{result}**")

@bot.command()
async def coin(ctx):
    await ctx.send(f"🪙 **{random.choice(['heads', 'tails'])}**")

@bot.command()
async def dice(ctx):
    await ctx.send(f"🎲 **{random.randint(1, 6)}**")

@bot.command()
async def joke(ctx):
    async with ctx.typing():
        await asyncio.sleep(1.0)
    await ctx.send(random.choice(JOKES))

@bot.command()
async def fact(ctx):
    async with ctx.typing():
        await asyncio.sleep(1.0)
    await ctx.send(f"📚 {random.choice(FACTS)}")

@bot.command()
async def vibe(ctx):
    vibes = ["vibing", "chilling", "surviving", "lowkey stressed", "thriving", "hungry", "unhinged", "plotting", "bored", "chaotic", "feral", "zen"]
    await ctx.send(f"currently {random.choice(vibes)} ngl")

@bot.command()
async def ping(ctx):
    ms = round(bot.latency * 1000)
    await ctx.send(f"pong! 🏓 `{ms}ms`")

@bot.command()
async def say(ctx, *, text: str):
    await ctx.send(text)

@bot.command()
async def avatar(ctx, member: discord.Member = None):
    target = member or ctx.author
    embed = discord.Embed(title=f"{target.display_name}'s avatar")
    embed.set_image(url=target.display_avatar.url)
    await ctx.send(embed=embed)

@bot.command()
async def userinfo(ctx, member: discord.Member = None):
    target = member or ctx.author
    embed = discord.Embed(title=target.display_name, color=target.color if target.color.value else discord.Color.default())
    embed.set_thumbnail(url=target.display_avatar.url)
    embed.add_field(name="ID", value=target.id, inline=True)
    embed.add_field(name="Joined Server", value=target.joined_at.strftime("%Y-%m-%d") if target.joined_at else "?", inline=True)
    embed.add_field(name="Account Created", value=target.created_at.strftime("%Y-%m-%d"), inline=True)
    embed.add_field(name="Top Role", value=target.top_role.mention, inline=True)
    await ctx.send(embed=embed)

@bot.command()
async def serverinfo(ctx):
    guild = ctx.guild
    embed = discord.Embed(title=guild.name, color=discord.Color.blurple())
    if guild.icon:
        embed.set_thumbnail(url=guild.icon.url)
    embed.add_field(name="Owner", value=guild.owner.mention if guild.owner else "?", inline=True)
    embed.add_field(name="Members", value=guild.member_count, inline=True)
    embed.add_field(name="Channels", value=len(guild.channels), inline=True)
    embed.add_field(name="Roles", value=len(guild.roles), inline=True)
    embed.add_field(name="Created", value=guild.created_at.strftime("%Y-%m-%d"), inline=True)
    await ctx.send(embed=embed)

@bot.command()
async def purge(ctx, amount: int = 5):
    if amount > 100:
        return await ctx.send("max 100")
    try:
        deleted = await ctx.channel.purge(limit=amount + 1)
        msg = await ctx.send(f"deleted {len(deleted)} messages")
        await asyncio.sleep(3)
        await msg.delete()
    except discord.Forbidden:
        await ctx.send("no perms")

@bot.command()
async def hug(ctx, member: discord.Member):
    await ctx.send(f"🤗 {ctx.author.display_name} hugs {member.display_name}!")

@bot.command()
async def slap(ctx, member: discord.Member):
    await ctx.send(f"👋 {ctx.author.display_name} slaps {member.display_name}!")

@bot.command()
async def kill(ctx, member: discord.Member = None):
    target = member or ctx.author
    await ctx.send(random.choice(DEATHS).format(name=target.display_name))

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        return
    if isinstance(error, commands.MissingRequiredArgument):
        await ctx.send("you're missing something")
    elif isinstance(error, commands.BadArgument):
        await ctx.send("that ain't right")
    elif isinstance(error, commands.MissingPermissions):
        await ctx.send("you don't have the juice for that")
    else:
        print(f"[K] command error: {error}")

bot.run(TOKEN)

