import os
import re
import discord
import random
import asyncio
import aiohttp
import time
from discord.ext import commands

TOKEN = os.getenv("DISCORD_BOT_TOKEN")

PREFIX = "!"
INTENTS = discord.Intents.default()
INTENTS.message_content = True
bot = commands.Bot(command_prefix=PREFIX, intents=INTENTS, help_command=None)

# ── proxy storage ──
proxies_db = {"http": [], "https": [], "socks4": [], "socks5": []}
last_scrape = 0

# ── free proxy sources ──
PROXY_SOURCES = {
    "http": [
        "https://www.proxy-list.download/api/v1/get?type=http",
        "https://api.proxyscrape.com/v2/?request=get&protocol=http&timeout=10000&country=all&ssl=all&anonymity=all",
        "https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/http.txt",
        "https://raw.githubusercontent.com/monosans/proxy-list/main/proxies/http.txt",
    ],
    "https": [
        "https://www.proxy-list.download/api/v1/get?type=https",
        "https://api.proxyscrape.com/v2/?request=get&protocol=https&timeout=10000&country=all&ssl=all&anonymity=all",
    ],
    "socks4": [
        "https://www.proxy-list.download/api/v1/get?type=socks4",
        "https://api.proxyscrape.com/v2/?request=get&protocol=socks4&timeout=10000&country=all",
        "https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/socks4.txt",
    ],
    "socks5": [
        "https://www.proxy-list.download/api/v1/get?type=socks5",
        "https://api.proxyscrape.com/v2/?request=get&protocol=socks5&timeout=10000&country=all",
        "https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/socks5.txt",
    ]
}

TEST_TIMEOUT = aiohttp.ClientTimeout(total=10)

# ── helpers ──
def parse_proxy_line(line, ptype):
    line = line.strip()
    if not line or line.startswith("#"):
        return None
    if ":" in line:
        parts = line.split(":")
        if len(parts) >= 2:
            ip = parts[0]
            port = parts[1].split()[0]
            if "." in ip:
                return {"ip": ip, "port": port, "type": ptype, "url": f"{ptype}://{ip}:{port}"}
    return None

def extract_proxies_from_text(text, ptype="http"):
    pattern = r'(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}):(\d{1,5})'
    matches = re.findall(pattern, text)
    proxies = []
    seen = set()
    for ip, port in matches:
        key = f"{ip}:{port}"
        if key not in seen:
            seen.add(key)
            proxies.append({"ip": ip, "port": port, "type": ptype, "url": f"{ptype}://{ip}:{port}"})
    return proxies

async def fetch_proxies(session, url):
    try:
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=15)) as resp:
            if resp.status == 200:
                text = await resp.text()
                return [l.strip() for l in text.splitlines() if l.strip()]
    except Exception:
        pass
    return []

async def scrape_all():
    global proxies_db, last_scrape
    proxies_db = {"http": [], "https": [], "socks4": [], "socks5": []}
    
    async with aiohttp.ClientSession() as session:
        tasks = []
        ptypes = []
        for ptype, urls in PROXY_SOURCES.items():
            for url in urls:
                tasks.append(fetch_proxies(session, url))
                ptypes.append(ptype)
        
        results = await asyncio.gather(*tasks)
        
        for ptype, lines in zip(ptypes, results):
            for line in lines:
                proxy = parse_proxy_line(line, ptype)
                if proxy and proxy not in proxies_db[ptype]:
                    proxies_db[ptype].append(proxy)
    
    last_scrape = time.time()
    total = sum(len(v) for v in proxies_db.values())
    return total

async def test_proxy(session, proxy):
    start = time.time()
    try:
        async with session.get(
            "http://httpbin.org/get", 
            proxy=proxy["url"], 
            timeout=TEST_TIMEOUT,
            ssl=False
        ) as resp:
            if resp.status == 200:
                elapsed = round((time.time() - start) * 1000)
                try:
                    data = await resp.json()
                    origin = data.get("origin", "unknown")
                    headers = data.get("headers", {})
                    
                    # anonymity detection
                    hdr_str = str(headers).lower()
                    xff = headers.get("X-Forwarded-For", headers.get("X-Forwarded-For", ""))
                    via = headers.get("Via", "")
                    x_real = headers.get("X-Real-Ip", "")
                    
                    if xff or x_real:
                        anonymity = "🔴 Transparent"
                    elif via or "proxy" in hdr_str or "squid" in hdr_str:
                        anonymity = "🟡 Anonymous"
                    else:
                        anonymity = "🟢 Elite"
                        
                except:
                    origin = "unknown"
                    anonymity = "❓ Unknown"
                return {"ok": True, "ms": elapsed, "origin": origin, "anonymity": anonymity}
    except Exception:
        pass
    return {"ok": False, "ms": 0, "origin": None, "anonymity": None}

async def test_proxies_from_db(ptype=None, max_test=50):
    connector = aiohttp.TCPConnector(ssl=False, limit=50)
    async with aiohttp.ClientSession(connector=connector) as session:
        pool = []
        if ptype and ptype in proxies_db:
            pool = proxies_db[ptype][:max_test * 2]
        else:
            for v in proxies_db.values():
                pool.extend(v[:max_test])
        
        random.shuffle(pool)
        pool = pool[:max_test]
        
        tasks = [test_proxy(session, p) for p in pool]
        results = await asyncio.gather(*tasks)
        
        working = []
        for proxy, result in zip(pool, results):
            if result["ok"]:
                proxy["ms"] = result["ms"]
                proxy["origin"] = result["origin"]
                proxy["anonymity"] = result["anonymity"]
                working.append(proxy)
        
        working.sort(key=lambda x: x["ms"])
        return working

async def test_proxies_list(proxy_list):
    connector = aiohttp.TCPConnector(ssl=False, limit=50)
    async with aiohttp.ClientSession(connector=connector) as session:
        tasks = [test_proxy(session, p) for p in proxy_list]
        results = await asyncio.gather(*tasks)
        
        working = []
        for proxy, result in zip(proxy_list, results):
            if result["ok"]:
                proxy["ms"] = result["ms"]
                proxy["origin"] = result["origin"]
                proxy["anonymity"] = result["anonymity"]
                working.append(proxy)
        
        working.sort(key=lambda x: x["ms"])
        return working

# ── events ──
@bot.event
async def on_ready():
    print(f"[K] proxy bot online as {bot.user}")
    print("[K] scraping proxies on startup...")
    total = await scrape_all()
    print(f"[K] scraped {total} proxies total")

# ── commands ──
@bot.command()
async def help(ctx):
    embed = discord.Embed(title="🌐 proxy bot commands", color=discord.Color.green())
    embed.add_field(name="!scrape", value="scrape fresh proxies from all sources", inline=False)
    embed.add_field(name="!proxies [type] [count]", value="get random proxies from db", inline=False)
    embed.add_field(name="!test [type] [count]", value="test proxies from db OR paste a list", inline=False)
    embed.add_field(name="!testlist <type>", value="reply to a proxy list message to test it", inline=False)
    embed.add_field(name="!testone <ip:port> [type]", value="test a single proxy", inline=False)
    embed.add_field(name="!stats", value="show scraped proxy counts", inline=False)
    embed.add_field(name="!random [type]", value="get one random proxy", inline=False)
    await ctx.send(embed=embed)

@bot.command()
async def scrape(ctx):
    msg = await ctx.send("scraping proxies from all sources... this might take a sec")
    total = await scrape_all()
    await msg.edit(content=f"scraped **{total}** proxies total\nhttp: {len(proxies_db['http'])} | https: {len(proxies_db['https'])} | socks4: {len(proxies_db['socks4'])} | socks5: {len(proxies_db['socks5'])}")

@bot.command()
async def stats(ctx):
    embed = discord.Embed(title="📊 proxy stats", color=discord.Color.blue())
    for ptype in ["http", "https", "socks4", "socks5"]:
        embed.add_field(name=ptype.upper(), value=str(len(proxies_db[ptype])), inline=True)
    if last_scrape:
        ago = int(time.time() - last_scrape)
        embed.set_footer(text=f"last scraped {ago}s ago")
    await ctx.send(embed=embed)

@bot.command()
async def randomproxy(ctx, ptype: str = "http"):
    ptype = ptype.lower()
    if ptype not in proxies_db or not proxies_db[ptype]:
        return await ctx.send(f"no {ptype} proxies available. run `!scrape` first.")
    p = random.choice(proxies_db[ptype])
    embed = discord.Embed(title="🎲 random proxy", color=discord.Color.orange())
    embed.add_field(name="IP", value=p["ip"], inline=True)
    embed.add_field(name="Port", value=p["port"], inline=True)
    embed.add_field(name="Type", value=p["type"].upper(), inline=True)
    embed.add_field(name="URL", value=f"`{p['url']}`", inline=False)
    await ctx.send(embed=embed)

@bot.command()
async def proxies(ctx, ptype: str = "http", count: int = 10):
    ptype = ptype.lower()
    if ptype not in proxies_db:
        return await ctx.send("valid types: http, https, socks4, socks5")
    if not proxies_db[ptype]:
        return await ctx.send(f"no {ptype} proxies scraped yet. run `!scrape` first.")
    
    count = min(count, 30)
    pool = random.sample(proxies_db[ptype], min(count, len(proxies_db[ptype])))
    
    lines = [f"{p['ip']}:{p['port']}" for p in pool]
    text = "\n".join(lines)
    
    if len(text) > 1900:
        text = text[:1900] + "\n...truncated"
    
    embed = discord.Embed(title=f"📋 {ptype.upper()} proxies ({len(pool)} shown)", color=discord.Color.teal())
    embed.description = f"```{text}```"
    await ctx.send(embed=embed)

@bot.command()
async def test(ctx, ptype: str = None, count: int = 20):
    ptype = ptype.lower() if ptype else "http"
    if ptype not in proxies_db:
        return await ctx.send("valid types: http, https, socks4, socks5")
    
    # ── check if user pasted proxies in this message or replied to a list ──
    target_text = ""
    
    # if replying to another message, grab its content
    if ctx.message.reference and ctx.message.reference.resolved:
        ref = ctx.message.reference.resolved
        if isinstance(ref, discord.Message):
            target_text += ref.content + "\n"
    
    # also grab any ip:port patterns from the current message after the command
    full_text = ctx.message.content
    # strip command
    cmd_stripped = full_text.replace(f"{PREFIX}test", "").strip()
    # remove first arg (type) and second arg (count if numeric)
    parts = cmd_stripped.split()
    extra_text = ""
    if len(parts) >= 2 and parts[1].isdigit():
        extra_text = " ".join(parts[2:])
    elif len(parts) >= 1:
        extra_text = " ".join(parts[1:])
    
    target_text += extra_text
    
    pasted_proxies = extract_proxies_from_text(target_text, ptype)
    
    if pasted_proxies:
        msg = await ctx.send(f"testing **{len(pasted_proxies)}** pasted proxies... please wait")
        working = await test_proxies_list(pasted_proxies)
        
        if not working:
            return await msg.edit(content="no working proxies found in your list.")
        
        lines = [f"{p['ip']}:{p['port']} | {p['ms']}ms | {p['anonymity']}" for p in working[:30]]
        text = "\n".join(lines)
        
        embed = discord.Embed(
            title=f"✅ working proxies ({len(working)}/{len(pasted_proxies)})",
            color=discord.Color.green()
        )
        if len(text) > 4000:
            # send as file if too long
            from io import StringIO
            file_text = "\n".join([f"{p['ip']}:{p['port']} | {p['ms']}ms | {p['anonymity']}" for p in working])
            file = discord.File(StringIO(file_text), filename="working_proxies.txt")
            await msg.edit(content=f"found **{len(working)}** working proxies:", attachments=[file])
            return
        
        embed.description = f"```{text}```"
        embed.set_footer(text="🟢 Elite = best | 🟡 Anonymous | 🔴 Transparent = worst")
        await msg.edit(content=None, embed=embed)
        return
    
    # ── fallback: test from database ──
    msg = await ctx.send(f"testing up to {count} proxies from database... please wait")
    working = await test_proxies_from_db(ptype, count)
    
    if not working:
        return await msg.edit(content="no working proxies found. free proxies die fast — try `!scrape` for fresh ones or paste your own list.")
    
    lines = [f"{p['ip']}:{p['port']} | {p['ms']}ms | {p['anonymity']}" for p in working[:20]]
    text = "\n".join(lines)
    
    embed = discord.Embed(
        title=f"✅ working proxies ({len(working)} found, top {len(lines)} shown)",
        color=discord.Color.green()
    )
    embed.description = f"```{text}```"
    embed.set_footer(text="sorted by speed | 🟢 Elite = best | 🟡 Anonymous | 🔴 Transparent")
    await msg.edit(content=None, embed=embed)

@bot.command()
async def testlist(ctx, ptype: str = "http"):
    """reply to a message containing proxies to test them"""
    ptype = ptype.lower()
    if ptype not in proxies_db:
        return await ctx.send("valid types: http, https, socks4, socks5")
    
    if not ctx.message.reference or not ctx.message.reference.resolved:
        return await ctx.send("reply to a message containing a proxy list to test it.")
    
    ref = ctx.message.reference.resolved
    if not isinstance(ref, discord.Message):
        return await ctx.send("could not read the replied message.")
    
    pasted_proxies = extract_proxies_from_text(ref.content, ptype)
    if not pasted_proxies:
        return await ctx.send("no valid ip:port proxies found in that message.")
    
    msg = await ctx.send(f"testing **{len(pasted_proxies)}** proxies from replied message...")
    working = await test_proxies_list(pasted_proxies)
    
    if not working:
        return await msg.edit(content="no working proxies found in that list.")
    
    lines = [f"{p['ip']}:{p['port']} | {p['ms']}ms | {p['anonymity']}" for p in working[:30]]
    text = "\n".join(lines)
    
    embed = discord.Embed(
        title=f"✅ working proxies ({len(working)}/{len(pasted_proxies)})",
        color=discord.Color.green()
    )
    if len(text) > 4000:
        from io import StringIO
        file_text = "\n".join([f"{p['ip']}:{p['port']} | {p['ms']}ms | {p['anonymity']}" for p in working])
        file = discord.File(StringIO(file_text), filename="working_proxies.txt")
        await msg.edit(content=f"found **{len(working)}** working proxies:", attachments=[file])
        return
    
    embed.description = f"```{text}```"
    embed.set_footer(text="🟢 Elite = best | 🟡 Anonymous | 🔴 Transparent = worst")
    await msg.edit(content=None, embed=embed)

@bot.command()
async def testone(ctx, proxy_str: str, ptype: str = "http"):
    if ":" not in proxy_str:
        return await ctx.send("format: `!testone ip:port [type]`")
    
    ip, port = proxy_str.split(":", 1)
    proxy = {"ip": ip, "port": port, "type": ptype, "url": f"{ptype}://{ip}:{port}"}
    
    msg = await ctx.send(f"testing {proxy_str}...")
    connector = aiohttp.TCPConnector(ssl=False)
    async with aiohttp.ClientSession(connector=connector) as session:
        result = await test_proxy(session, proxy)
    
    if result["ok"]:
        embed = discord.Embed(title="✅ proxy works", color=discord.Color.green())
        embed.add_field(name="Proxy", value=proxy_str, inline=True)
        embed.add_field(name="Response", value=f"{result['ms']}ms", inline=True)
        embed.add_field(name="Anonymity", value=result["anonymity"], inline=True)
        embed.add_field(name="Origin IP", value=result["origin"], inline=True)
    else:
        embed = discord.Embed(title="❌ proxy dead", color=discord.Color.red())
        embed.add_field(name="Proxy", value=proxy_str, inline=False)
    
    await msg.edit(content=None, embed=embed)

@bot.command()
async def export(ctx, ptype: str = "http"):
    ptype = ptype.lower()
    if ptype not in proxies_db or not proxies_db[ptype]:
        return await ctx.send(f"no {ptype} proxies available.")
    
    lines = [f"{p['ip']}:{p['port']}" for p in proxies_db[ptype]]
    text = "\n".join(lines)
    
    if len(text) > 1900:
        from io import StringIO
        file = discord.File(StringIO(text), filename=f"{ptype}_proxies.txt")
        await ctx.send(f"📁 here's your {ptype} proxy list:", file=file)
    else:
        await ctx.send(f"```{text}```")

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        return
    if isinstance(error, commands.MissingRequiredArgument):
        await ctx.send("you're missing an argument. check `!help`")
    else:
        print(f"[K] error: {error}")

bot.run(TOKEN)
