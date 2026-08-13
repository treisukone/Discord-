import os
import discord
import asyncio
import aiohttp
import random
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

TEST_URL = "http://httpbin.org/ip"
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
            if ip.replace(".", "").isdigit() or "." in ip:
                return {"ip": ip, "port": port, "type": ptype, "url": f"{ptype}://{ip}:{port}"}
    return None

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
        for ptype, urls in PROXY_SOURCES.items():
            for url in urls:
                tasks.append((ptype, fetch_proxies(session, url)))
        
        results = await asyncio.gather(*[t[1] for t in tasks])
        ptypes = [t[0] for t in tasks]
        
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
        connector = aiohttp.TCPConnector(ssl=False)
        async with session.get(
            TEST_URL, 
            proxy=proxy["url"], 
            timeout=TEST_TIMEOUT,
            connector=connector
        ) as resp:
            if resp.status == 200:
                elapsed = round((time.time() - start) * 1000)
                data = await resp.json()
                origin = data.get("origin", "unknown")
                return {"ok": True, "ms": elapsed, "origin": origin}
    except Exception as e:
        pass
    return {"ok": False, "ms": 0, "origin": None}

async def test_proxies(ptype=None, max_test=50):
    async with aiohttp.ClientSession() as session:
        pool = []
        if ptype and ptype in proxies_db:
            pool = proxies_db[ptype][:max_test]
        else:
            for v in proxies_db.values():
                pool.extend(v[:max_test // 4])
        
        random.shuffle(pool)
        pool = pool[:max_test]
        
        tasks = [test_proxy(session, p) for p in pool]
        results = await asyncio.gather(*tasks)
        
        working = []
        for proxy, result in zip(pool, results):
            if result["ok"]:
                proxy["ms"] = result["ms"]
                proxy["origin"] = result["origin"]
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
    embed.add_field(name="!proxies [type] [count]", value="get working proxies (types: http/https/socks4/socks5)", inline=False)
    embed.add_field(name="!test [type] [count]", value="test scraped proxies and return working ones", inline=False)
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
    ptype = ptype.lower() if ptype else None
    if ptype and ptype not in proxies_db:
        return await ctx.send("valid types: http, https, socks4, socks5")
    
    msg = await ctx.send(f"testing up to {count} proxies... please wait")
    working = await test_proxies(ptype, count)
    
    if not working:
        return await msg.edit(content="no working proxies found. try `!scrape` to get fresh ones.")
    
    lines = [f"{p['ip']}:{p['port']} | {p['ms']}ms | origin: {p['origin']}" for p in working[:20]]
    text = "\n".join(lines)
    
    embed = discord.Embed(
        title=f"✅ working proxies ({len(working)} found, top {len(lines)} shown)",
        color=discord.Color.green()
    )
    embed.description = f"```{text}```"
    embed.set_footer(text="sorted by response time (fastest first)")
    await msg.edit(content=None, embed=embed)

@bot.command()
async def testone(ctx, proxy_str: str, ptype: str = "http"):
    if ":" not in proxy_str:
        return await ctx.send("format: `!testone ip:port [type]`")
    
    ip, port = proxy_str.split(":", 1)
    proxy = {"ip": ip, "port": port, "type": ptype, "url": f"{ptype}://{ip}:{port}"}
    
    msg = await ctx.send(f"testing {proxy_str}...")
    async with aiohttp.ClientSession() as session:
        result = await test_proxy(session, proxy)
    
    if result["ok"]:
        embed = discord.Embed(title="✅ proxy works", color=discord.Color.green())
        embed.add_field(name="Proxy", value=proxy_str, inline=True)
        embed.add_field(name="Response", value=f"{result['ms']}ms", inline=True)
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
    
    # send as file if too long
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
