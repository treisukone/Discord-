(async () => {
    const { Worker } = await import("worker_threads");
    const path = await import("path");
    const { WebSocketServer } = await import("ws");
    const { pack, unpack } = await import("msgpackr");
    const http = await import("http");
    const fetchModule = await import("node-fetch");
    const realFetch = fetchModule.default || fetchModule;
    const { Client, GatewayIntentBits } = await import("discord.js");

    const noop = () => {};
    const _clog = console.log; console.log = noop; console.error = noop; console.warn = noop;

    // ── config ──
    let PROXIES = process.env.PROXIES ? process.env.PROXIES.split(",") : [
        "http://roJ9QRyWGL6-zone-custom:7feff09c1e63@proxy.ipmax.cc:10000"
    ];
    const PREFIX = "!";
    const WORKER_MEMORY_MB = 96;
    const BOTS_PER_WORKER = 8;
    const PREWARM_POOL_SIZE = 8;
    const TOKEN = process.env.DISCORD_BOT_TOKEN;

    let arrasScriptCache = null;
    let arrasWasmCache = null;

    // ── discord client ──
    const client = new Client({
        intents: [
            GatewayIntentBits.Guilds,
            GatewayIntentBits.GuildMessages,
            GatewayIntentBits.MessageContent
        ]
    });

    // ── http + ws server ──
    const server = http.createServer((req, res) => {
        res.writeHead(426, { "Content-Type": "text/plain" });
        res.end("lll elk ez big fat noob");
    });

    function randint(a, b) {
        return Math.floor(Math.random() * (b - a + 1)) + a;
    }

    const botWorkerPath = path.join(__dirname, "index.js");

    function extractArrasScript(html) {
        const scriptTagStart = html.indexOf("<script>");
        if (scriptTagStart === -1) throw new Error("Could not find arras script tag");
        const scriptStart = scriptTagStart + 8;
        const scriptTagEnd = html.indexOf("</script", scriptStart);
        if (scriptTagEnd === -1) throw new Error("Could not find arras script close tag");
        return html.slice(scriptStart, scriptTagEnd);
    }

    async function preloadArrasAssets() {
        try {
            const [htmlRes, wasmRes] = await Promise.all([
                realFetch("https://arras.io"),
                realFetch("https://arras.io/app.wasm")
            ]);
            const html = await htmlRes.text();
            const wasm = await wasmRes.arrayBuffer();
            arrasScriptCache = extractArrasScript(html);
            arrasWasmCache = new Uint8Array(wasm);
        } catch (err) {
            _clog("preload failed:", err);
        }
    }

    function createBotWorker(session) {
        const worker = new Worker(botWorkerPath, {
            resourceLimits: {
                maxOldGenerationSizeMb: WORKER_MEMORY_MB,
                maxYoungGenerationSizeMb: 32,
                codeRangeSizeMb: 32,
            }
        });
        worker.send = (message) => worker.postMessage(message);
        worker.botId = null;
        worker.botIds = [];
        worker.activeBots = 0;
        worker.isPooled = false;
        worker.resolvedHash = null;
        worker.on("error", (err) => { });
        worker.on("message", (message) => {
            if (!message) return;
            if (message.type === "died") {
                const idx = worker.botIds.indexOf(message.id);
                if (idx !== -1) worker.botIds.splice(idx, 1);
                worker.activeBots = Math.max(0, worker.activeBots - 1);
            } else if (message.type === "hash_update") {
                if (message.hash) {
                    worker.resolvedHash = message.hash;
                    if (session) {
                        session.resolvedHash = message.hash;
                        if (session.ws) session.ws.send(pack(["R", message.hash]));
                    }
                }
            }
        });
        worker.on("exit", (code) => {
            let idx = session.workers.indexOf(worker);
            if (idx !== -1) session.workers.splice(idx, 1);
            idx = session.pool.indexOf(worker);
            if (idx !== -1) session.pool.splice(idx, 1);
        });
        return worker;
    }

    function prepareWorker(worker) {
        worker.send({ type: "prepare", arrasCache: arrasScriptCache, wasmCache: arrasWasmCache });
    }

    function fillPool(session) {
        const total = session.workers.length + session.pool.length;
        const needed = Math.max(0, PREWARM_POOL_SIZE - total);
        for (let i = 0; i < needed; i++) {
            const worker = createBotWorker(session);
            worker.isPooled = true;
            session.pool.push(worker);
            prepareWorker(worker);
        }
    }

    function acquireWorker(session) {
        let worker = session.workers.find((candidate) => candidate.activeBots < BOTS_PER_WORKER);
        if (worker) return worker;
        worker = session.pool.shift() || createBotWorker(session);
        worker.isPooled = false;
        if (!session.workers.includes(worker)) session.workers.push(worker);
        return worker;
    }

    function spawnBotNow(session, hash, botName) {
        if (session.proxyIdx >= PROXIES.length) session.proxyIdx = 0;
        const worker = acquireWorker(session);
        const botId = session.nextBotId++;
        worker.botId = botId;
        worker.botIds.push(botId);
        worker.activeBots++;

        let selectedTank = session.tank;
        if (session.tanks.length) {
            selectedTank = session.tanks[session.tankIdx];
            session.tankIdx = (session.tankIdx + 1) % session.tanks.length;
        }

        const spawnHash = session.resolvedHash ? "#" + session.resolvedHash : "#" + hash;
        worker.send({
            type: "start",
            config: {
                id: botId,
                proxy: { type: "http", url: PROXIES[session.proxyIdx] },
                hash: spawnHash,
                name: botName,
                stats: [0, 0, 0, 0, 0, 0, 0, 9],
                type: "follow",
                token: "follow-8fe6ca",
                autoFire: false,
                autoRespawn: true,
                keys: [],
                keysHold: [],
                tank: "Auto4",
                chatSpam: "",
                initialTarget: { tank: selectedTank },
                squadId: hash,
                reconnectAttempts: 5,
                reconnectDelay: 8000,
                arrasCache: arrasScriptCache,
                wasmCache: arrasWasmCache,
                teamColor: session.teamColor,
            }
        });
        session.proxyIdx = (session.proxyIdx + 1) % PROXIES.length;
    }

    function queueBotSpawn(session, hash, botName) {
        spawnBotNow(session, hash, botName);
    }

    function destroySession(session) {
        session.spawnQueue = [];
        session.spawnQueueActive = false;
        if (session.spawnTimer) { clearTimeout(session.spawnTimer); session.spawnTimer = null; }
        for (const worker of session.workers) {
            worker.send({ type: "destroy" });
            worker.botIds = [];
            worker.activeBots = 0;
        }
        session.workers = [];
        fillPool(session);
    }

    function sendPositionUpdate(session, patch) {
        const payload = {
            type: "position",
            x: 0, y: 0,
            mouseX: 0, mouseY: 0,
            mouseDown: false, rMouseDown: false,
            mouse: false, feeding: false,
            shift: false,
            autofire: false,
            autospin: false,
            manualMode: false,
            manualX: 0,
            manualY: 0,
            teamColor: session.teamColor,
            ...patch
        };
        for (const worker of session.workers) {
            worker.send(payload);
        }
    }

    // ── discord session (persistent) ──
    const discordSession = {
        workers: [],
        pool: [],
        spawnQueue: [],
        spawnQueueActive: false,
        spawnTimer: null,
        nextBotId: 0,
        tank: "auto6",
        tanks: [],
        tankIdx: 0,
        proxyIdx: 0,
        resolvedHash: null,
        teamColor: null,
        ws: null
    };
    fillPool(discordSession);

    // ── discord commands ──
    client.on("messageCreate", async (msg) => {
        if (msg.author.bot || !msg.content.startsWith(PREFIX)) return;
        const args = msg.content.slice(PREFIX.length).trim().split(/ +/);
        const cmd = args.shift().toLowerCase();

        switch (cmd) {
            case "help": {
                const embed = {
                    color: 0x5865F2,
                    title: "🎮 arras bot controller",
                    fields: [
                        { name: "!spawn <hash> [count] [name]", value: "spawn bots to server hash" },
                        { name: "!goto <x> <y>", value: "send all bots to coordinates" },
                        { name: "!tank <tank>", value: "change tank class" },
                        { name: "!destroy", value: "kill all bots" },
                        { name: "!status", value: "show active bot count" },
                        { name: "!autofire", value: "toggle autofire" },
                        { name: "!feed", value: "toggle feed mode" },
                        { name: "!proxy <url>", value: "set proxy (http://ip:port)" },
                        { name: "!proxies", value: "show current proxy list" },
                    ]
                };
                msg.channel.send({ embeds: [embed] });
                break;
            }

            case "spawn": {
                const hash = args[0];
                const count = parseInt(args[1]) || 1;
                const name = args.slice(2).join(" ") || "Bot";
                if (!hash) return msg.reply("usage: `!spawn <hash> [count] [name]`");
                for (let i = 0; i < count; i++) queueBotSpawn(discordSession, hash, name);
                msg.reply(`spawning **${count}** bot(s) to \`${hash}\` as **${name}**`);
                break;
            }

            case "goto": {
                const x = parseFloat(args[0]);
                const y = parseFloat(args[1]);
                if (isNaN(x) || isNaN(y)) return msg.reply("usage: `!goto <x> <y>`");
                sendPositionUpdate(discordSession, { manualMode: true, manualX: x, manualY: y });
                msg.reply(`bots moving to **${x}, ${y}**`);
                break;
            }

            case "tank": {
                const tank = args[0];
                if (!tank) return msg.reply("usage: `!tank <tankname>`");
                discordSession.tank = tank;
                discordSession.tanks = [];
                for (const worker of discordSession.workers) {
                    worker.send({ type: "tankselect", tank: tank });
                }
                msg.reply(`tank set to **${tank}**`);
                break;
            }

            case "destroy": {
                const total = discordSession.workers.reduce((sum, w) => sum + w.activeBots, 0);
                destroySession(discordSession);
                msg.reply(`destroyed **${total}** bot(s)`);
                break;
            }

            case "status": {
                const total = discordSession.workers.reduce((sum, w) => sum + w.activeBots, 0);
                const workers = discordSession.workers.length;
                msg.reply(`**${total}** active bot(s) across **${workers}** worker(s)`);
                break;
            }

            case "autofire": {
                discordSession.autofire = !discordSession.autofire;
                sendPositionUpdate(discordSession, { autofire: discordSession.autofire });
                msg.reply(`autofire **${discordSession.autofire ? "ON" : "OFF"}**`);
                break;
            }

            case "feed": {
                discordSession.feeding = !discordSession.feeding;
                sendPositionUpdate(discordSession, { feeding: discordSession.feeding });
                msg.reply(`feed mode **${discordSession.feeding ? "ON" : "OFF"}**`);
                break;
            }

            case "proxy": {
                const url = args[0];
                if (!url) return msg.reply("usage: `!proxy <http://ip:port>`");
                PROXIES = [url];
                msg.reply(`proxy set to \`${url}\``);
                break;
            }

            case "proxies": {
                msg.reply(`current proxies:\n\`\`\`\n${PROXIES.join("\n")}\n\`\`\``);
                break;
            }

            default:
                break;
        }
    });

    client.once("ready", () => {
        _clog(`[discord] logged in as ${client.user.tag}`);
    });

    await client.login(TOKEN);

    // ── original websocket server (kept for compatibility) ──
    const sessions = new Map();
    const wss = new WebSocketServer({ server });

    wss.on("connection", (ws, req) => {
        const addr = req.socket.remoteAddress;
        if (!sessions.has(addr)) {
            sessions.set(addr, {
                workers: [], pool: [], spawnQueue: [], spawnQueueActive: false,
                spawnTimer: null, nextBotId: 0, tank: "auto6", tanks: [],
                tankIdx: 0, proxyIdx: 0, resolvedHash: null, teamColor: null
            });
        }
        const session = sessions.get(addr);
        session.ws = ws;
        let challenge;
        let verified = false;

        function packet(...args) { ws.send(pack(args)); }
        function close() { ws.close(); }

        ws.on("message", (msg) => {
            try {
                const data = unpack(msg);
                const type = data.shift();
                switch (type) {
                    case "M":
                        if (challenge || data[0] != 72011) { close(); return; }
                        challenge = randint(0b1000000000, 0b1111111111);
                        packet("M", challenge);
                        break;
                    case "C":
                        if (data[0] == (challenge ^ 845)) {
                            verified = true;
                            fillPool(session);
                        } else { close(); }
                        break;
                    case "Z":
                        session.tank = data[0];
                        if (session.tank instanceof Array) {
                            session.tanks = session.tank;
                            session.tankIdx = 0;
                            for (const worker of session.workers) {
                                for (const botId of worker.botIds) {
                                    const t = session.tanks[session.tankIdx];
                                    worker.send({ type: "tankselect", tank: t, botId });
                                    session.tankIdx = (session.tankIdx + 1) % session.tanks.length;
                                }
                            }
                        } else {
                            session.tanks = [];
                            for (const worker of session.workers) {
                                worker.send({ type: "tankselect", tank: session.tank });
                            }
                        }
                        break;
                    case "F":
                        if (verified) {
                            const hash = data[0];
                            const count = parseInt(data[1]) || 1;
                            const botName = String(data[2] || "Bot").trim() || "Bot";
                            for (let i = 0; i < count; i++) queueBotSpawn(session, hash, botName);
                        }
                        break;
                    case "B":
                        if (verified) destroySession(session);
                        break;
                    case "A":
                        if (verified) {
                            for (const worker of session.workers) {
                                worker.send({
                                    type: "position",
                                    x: data[0], y: data[1],
                                    mouseX: data[2], mouseY: data[3],
                                    mouseDown: data[4], rMouseDown: data[5],
                                    mouse: data[6], feeding: data[7],
                                    shift: data[8], autofire: data[9],
                                    autospin: data[10], manualMode: data[11],
                                    manualX: data[12], manualY: data[13],
                                    teamColor: session.teamColor,
                                });
                            }
                        }
                        break;
                    case "T":
                        if (verified) {
                            for (const worker of session.workers) {
                                worker.send({ type: "chat", message: data[0], spam: data[1] });
                            }
                        }
                        break;
                    case "H":
                        if (verified) {
                            const detectedTeam = String(data[0] || "").toLowerCase().trim();
                            const validTeams = ["green", "blue", "pink", "purple"];
                            if (validTeams.includes(detectedTeam)) {
                                const prevTeam = session.teamColor;
                                session.teamColor = detectedTeam;
                                if (prevTeam !== detectedTeam) {
                                    for (const worker of session.workers) {
                                        worker.send({ type: "teamcolor", teamColor: detectedTeam });
                                    }
                                }
                            }
                        }
                        break;
                    default:
                        close();
                        break;
                }
            } catch (e) { }
        });

        ws.on("close", () => { });
    });

    const port = process.env.PORT || 8082;
    await preloadArrasAssets();
    server.listen(port, () => {
        _clog("Server ready on port", port);
    });
})();
