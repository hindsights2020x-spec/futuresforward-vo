# FuturesForged — Virtual Office

24/7 cloud dashboard + Telegram bot + workflow tree, backed by Supabase.
Plugs into the existing TradingBot via a single drop-in module (`vo_client.py`).

## What's in the box

```
virtual_office/
├── install.bat                 ← run this on the TradingBot machine
├── render.yaml                 ← Render blueprint: web + worker
├── requirements.txt
├── .env.example
├── supabase/
│   ├── schema.sql              ← run once in Supabase SQL editor
│   └── seed_workflow_tree.sql  ← seeds the tree from memory
├── server/
│   ├── web_app.py              ← Flask dashboard + REST API
│   ├── worker.py               ← Telegram bot (long-poll)
│   ├── vo_db.py                ← Supabase REST wrapper
│   └── templates/
│       ├── index.html          ← dashboard landing
│       └── workflow_tree.html  ← custom tree visualizer
├── client/
│   └── vo_client.py            ← drops into TradingBot/, imported by bot_engine
└── scripts/
    └── seed_tree.py            ← Python alternative to seed via REST
```

## One-time setup (~10 min)

### 1. Supabase
1. Create a new project at supabase.com.
2. Project settings → API → copy the `service_role` key (NOT anon).
3. SQL Editor → New query → paste `supabase/schema.sql` → Run.
4. SQL Editor → New query → paste `supabase/seed_workflow_tree.sql` → Run.

### 2. Telegram
1. Talk to `@BotFather` → `/newbot` → save the token.
2. Send any message to your new bot from your phone.
3. Visit `https://api.telegram.org/bot<TOKEN>/getUpdates` → copy your `chat.id`.

### 3. Render
1. Push this folder to a GitHub repo (or use the existing one).
2. Render dashboard → **New** → **Blueprint** → point at the repo.
3. It'll detect `render.yaml` and create two services: `vo-web` + `vo-worker`.
4. In each service's **Environment** tab, paste:
   - `SUPABASE_URL`
   - `SUPABASE_SERVICE_KEY` (the service-role JWT)
   - (worker only) `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`, `VO_WEB_URL`
5. Deploy.

### 4. Bot side — wire `vo_client.py` into `bot_engine.py`
1. Run `install.bat` (or copy `client/vo_client.py` to `C:\Users\TOM\Desktop\TradingBot\`).
2. Add to the TradingBot `.env`:
   ```
   SUPABASE_URL=https://yourproject.supabase.co
   SUPABASE_SERVICE_KEY=...service_role...
   VO_ENABLED=1
   ```
3. In `bot_engine.py`, just below `load_dotenv(...)`, add:
   ```python
   import vo_client
   vo_client.log_event("bot starting", level="info")
   ```
4. See the HOOK GUIDE block at the bottom of `vo_client.py` for the other
   four wiring points (snapshots, trades, pending signals, errors).

## Pending-signal buttons

The data model is fully scaffolded but **approve/reject buttons are OFF by default**
in both the dashboard and Telegram. To turn them on, set on each Render service:

```
VO_ENABLE_SIGNAL_BUTTONS=1
```

Re-deploy. Until then, signals are recorded for observability but the bot
remains fully autonomous.

## What you get

| Surface       | What it shows                                              |
|---------------|------------------------------------------------------------|
| `/`           | Live events, trades, pending signals, account snapshots    |
| `/tree`       | Interactive workflow tree — strategies, infra, Cowork, decisions |
| Telegram      | Push alerts on every trade + warn/error event              |
| Telegram cmds | `/status` `/trades` `/pending` `/tree` `/health`           |

## Costs

Render free tier covers both services. Supabase free tier (500MB / 50k MAUs)
is plenty for this volume.
