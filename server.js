(async () => {
    const { Worker } = await import("worker_threads");
    const path = await import("path");
    const { Client, GatewayIntentBits } = await import("discord.js");
    const fetchModule = await import("node-fetch");
    const realFetch = fetchModule.default || fetchModule;

    const TOKEN = process.env.DISCORD_BOT_TOKEN;
    const PREFIX = "!";
    let PROXIES = process.env.PROXIES ? process.env.PROXIES.split(",") : [];

    let arrasScriptCache = null;
    let arrasWasmCache = null;

    const client = new Client({
        intents: [GatewayIntentBits.Guilds, GatewayIntentBits.GuildMessages, GatewayIntentBits.MessageContent]
    });

    const botWorkerPath = path.join(__dirname, "index.js");

    function extractArrasScript(html) {
        const start = html.indexOf("<script>");
        const end = html.indexOf("</script", start);
        return html.slice(start + 8, end);
    }

    async function preloadArrasAssets() {
        const [htmlRes, wasmRes] = await Promise.all([
            realFetch("https://arras.io"),
            realFetch("https://arras.io/app.wasm")
        ]);
        arrasScriptCache = extractArrasScript(await htmlRes.text());
        arrasWasmCache = new Uint8Array(await wasmRes.arrayBuffer());
    }

    function createWorker() {
        return new Worker(botWorkerPath, {
            resourceLimits: { maxOldGenerationSizeMb: 96, maxYoungGenerationSizeMb: 32, codeRangeSizeMb: 32 }
        });
    }

    function prepareWorker(worker) {
        worker.postMessage({ type: "prepare", arrasCache: arrasScriptCache, wasmCache: arrasWasmCache });
    }

    // ── session ──
    const session = {
        workers: [],
        pool: [],
        nextBotId: 0,
        proxyIdx: 0,
        tank: "basic",
        resolvedHash: null
    };

    function fillPool() {
        while (session.pool.length < 4) {
            const w = createWorker();
            session.pool.push(w);
            prepareWorker(w);
        }
    }

    function getWorker() {
        let w = session.workers.find(w => w.activeBots < 8);
        if (w) return w;
        w = session.pool.shift() || createWorker();
        if (!session.workers.includes(w)) session.workers.push(w);
        return w;
    }

    function spawnBot(hash, name) {
        if (!PROXIES.length) return;
        if (session.proxyIdx >= PROXIES.length) session.proxyIdx = 0;

        const w = getWorker();
        const id = session.nextBotId++;
        w.activeBots = (w.activeBots || 0) + 1;
        w.botIds = w.botIds || [];
        w.botIds.push(id);

        w.postMessage({
            type: "start",
            config: {
                id,
                proxy: { type: "http", url: PROXIES[session.proxyIdx] },
                hash: "#" + hash,
                name: name || "Bot",
                stats: [0, 0, 0, 0, 0, 0, 0, 9],
                type: "follow",
                token: "follow-8fe6ca",
                autoRespawn: true,
                keys: [],
                keysHold: [],
                tank: session.tank,
                chatSpam: "",
                initialTarget: { tank: session.tank },
                squadId: hash,
                reconnectAttempts: 5,
                reconnectDelay: 8000,
                arrasCache: arrasScriptCache,
                wasmCache: arrasWasmCache
            }
        });

        session.proxyIdx = (session.proxyIdx + 1) % PROXIES.length;
    }

    function sendPos(x, y) {
        for (const w of session.workers) {
            w.postMessage({
                type: "position",
                x: 0, y: 0,
                mouseX: 0, mouseY: 0,
                mouseDown: false, rMouseDown: false,
                mouse: false, feeding: false,
                shift: false, autofire: false, autospin: false,
                manualMode: true, manualX: x, manualY: y,
                teamColor: null
            });
        }
    }

    function destroyAll() {
        for (const w of session.workers) {
            w.postMessage({ type: "destroy" });
            w.activeBots = 0;
            w.botIds = [];
        }
        session.workers = [];
        fillPool();
    }

    function getTotalBots() {
        return session.workers.reduce((sum, w) => sum + (w.activeBots || 0), 0);
    }

    // ── discord ──
    client.on("messageCreate", async (msg) => {
        if (msg.author.bot || !msg.content.startsWith(PREFIX)) return;
        const args = msg.content.slice(PREFIX.length).trim().split(/ +/);
        const cmd = args.shift().toLowerCase();

        if (cmd === "help") {
            return msg.channel.send(
                "```\n" +
                "!spawn <count> <hash> [name]  - spawn bots\n" +
                "!goto <x> <y>                 - move bots to coords\n" +
                "!destroy                      - kill all bots\n" +
                "!status                       - bot count\n" +
                "!tank <name>                  - change tank class\n" +
                "```"
            );
        }

        if (cmd === "spawn") {
            const count = parseInt(args[0]);
            const hash = args[1];
            const name = args.slice(2).join(" ") || "Bot";
            if (!count || !hash) return msg.reply("usage: `!spawn <count> <hash> [name]`");
            if (!PROXIES.length) return msg.reply("no proxies set. add `PROXIES` env var.");
            for (let i = 0; i < count; i++) spawnBot(hash.replace("#", ""), name);
            return msg.reply(`spawning **${count}** bot(s) to \`${hash}\``);
        }

        if (cmd === "goto") {
            const x = parseFloat(args[0]);
            const y = parseFloat(args[1]);
            if (isNaN(x) || isNaN(y)) return msg.reply("usage: `!goto <x> <y>`");
            sendPos(x, y);
            return msg.reply(`moving to **${x}, ${y}**`);
        }

        if (cmd === "destroy") {
            const total = getTotalBots();
            destroyAll();
            return msg.reply(`killed **${total}** bot(s)`);
        }

        if (cmd === "status") {
            return msg.reply(`**${getTotalBots()}** active bot(s)`);
        }

        if (cmd === "tank") {
            const tank = args[0];
            if (!tank) return msg.reply("usage: `!tank <tankname>`");
            session.tank = tank;
            for (const w of session.workers) {
                w.postMessage({ type: "tankselect", tank });
            }
            return msg.reply(`tank set to **${tank}**`);
        }
    });

    client.once("ready", () => {
        console.log(`[K] discord ready as ${client.user.tag}`);
    });

    await preloadArrasAssets();
    fillPool();
    await client.login(TOKEN);
})();
