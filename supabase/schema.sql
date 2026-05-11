-- ============================================================
-- FuturesForged Virtual Office — Supabase Schema
-- ============================================================
-- Run once on a fresh Supabase project: Database → SQL Editor → paste → Run
-- ============================================================

-- ── EVENTS (system log: errors, info, warnings, lifecycle) ──
create table if not exists events (
    id          bigserial primary key,
    ts          timestamptz not null default now(),
    source      text not null,           -- 'bot_engine' | 'web' | 'worker' | 'ninjatrader' | ...
    level       text not null default 'info',  -- info | warn | error | trade | signal
    account_id  text,                    -- optional
    message     text not null,
    payload     jsonb default '{}'::jsonb
);
create index if not exists events_ts_idx     on events(ts desc);
create index if not exists events_level_idx  on events(level);
create index if not exists events_source_idx on events(source);

-- ── TRADES (executed) ──
create table if not exists trades (
    id           bigserial primary key,
    ts           timestamptz not null default now(),
    account_id   text not null,
    strategy     text not null,
    instrument   text not null,          -- NQ | MNQ | ES | MES
    direction    text not null,          -- LONG | SHORT
    qty          int  not null,
    entry        numeric,
    stop         numeric,
    tp           numeric,
    exit_price   numeric,
    exit_reason  text,                   -- TP | STOP | EOD | MANUAL
    pnl          numeric,
    raw          jsonb default '{}'::jsonb
);
create index if not exists trades_ts_idx     on trades(ts desc);
create index if not exists trades_acct_idx   on trades(account_id);
create index if not exists trades_strat_idx  on trades(strategy);

-- ── ACCOUNT SNAPSHOTS (periodic state) ──
create table if not exists account_snapshots (
    id              bigserial primary key,
    ts              timestamptz not null default now(),
    account_id      text not null,
    balance         numeric,
    floor           numeric,
    floor_locked    boolean,
    intraday_hwm    numeric,
    eod_hwm         numeric,
    passed          boolean,
    cum_profit      numeric,
    open_position   jsonb default '{}'::jsonb,
    rules_snapshot  jsonb default '{}'::jsonb
);
create index if not exists snap_ts_idx   on account_snapshots(ts desc);
create index if not exists snap_acct_idx on account_snapshots(account_id);

-- ── PENDING SIGNALS (pre-execution — scaffolded, buttons OFF by default) ──
create table if not exists pending_signals (
    id           bigserial primary key,
    ts           timestamptz not null default now(),
    account_id   text not null,
    strategy     text not null,
    instrument   text not null,
    direction    text not null,
    qty          int  not null,
    entry        numeric,
    stop         numeric,
    tp           numeric,
    rationale    text,
    status       text not null default 'pending',  -- pending | approved | rejected | expired | auto_taken
    decided_by   text,                              -- 'telegram' | 'web' | 'bot_auto'
    decided_at   timestamptz,
    expires_at   timestamptz,
    raw          jsonb default '{}'::jsonb
);
create index if not exists ps_ts_idx     on pending_signals(ts desc);
create index if not exists ps_status_idx on pending_signals(status);

-- ============================================================
-- WORKFLOW TREE (replaces project_tree_preview.html hardcoded data)
-- ============================================================
-- Concept: each node = a piece of work, decision, strategy, infra,
-- or doc. Edges link parents to children. Params hold structured
-- data for any node (e.g. strategy phase params). Status is mutable.
-- Decisions record reasoning/outcomes attached to nodes.
-- ============================================================

create table if not exists nodes (
    id           text primary key,           -- slug: 'strat.sweep_reverse'
    title        text not null,
    kind         text not null,              -- strategy | cowork | infra | decision | doc | phase | account
    summary      text,
    created_at   timestamptz default now(),
    updated_at   timestamptz default now(),
    meta         jsonb default '{}'::jsonb
);
create index if not exists nodes_kind_idx on nodes(kind);

create table if not exists edges (
    id           bigserial primary key,
    from_node    text not null references nodes(id) on delete cascade,
    to_node      text not null references nodes(id) on delete cascade,
    relation     text not null default 'parent_of',  -- parent_of | depends_on | blocks | informs
    created_at   timestamptz default now(),
    unique(from_node, to_node, relation)
);
create index if not exists edges_from_idx on edges(from_node);
create index if not exists edges_to_idx   on edges(to_node);

create table if not exists node_params (
    id           bigserial primary key,
    node_id      text not null references nodes(id) on delete cascade,
    key          text not null,
    value        jsonb not null,
    updated_at   timestamptz default now(),
    unique(node_id, key)
);
create index if not exists np_node_idx on node_params(node_id);

create table if not exists node_status (
    node_id      text primary key references nodes(id) on delete cascade,
    status       text not null,           -- idea | active | blocked | passed | shelved | live | done
    progress     int default 0,           -- 0..100
    blocker      text,
    updated_at   timestamptz default now()
);

create table if not exists decisions (
    id           bigserial primary key,
    node_id      text references nodes(id) on delete set null,
    ts           timestamptz default now(),
    title        text not null,
    rationale    text,
    outcome      text,                    -- chosen | rejected | deferred
    payload      jsonb default '{}'::jsonb
);
create index if not exists dec_node_idx on decisions(node_id);
create index if not exists dec_ts_idx   on decisions(ts desc);

-- ============================================================
-- VIEW: full tree (handy for the visualizer API)
-- ============================================================
create or replace view v_tree as
select
    n.id, n.title, n.kind, n.summary, n.meta,
    coalesce(s.status,'idea')   as status,
    coalesce(s.progress,0)      as progress,
    s.blocker,
    (select coalesce(jsonb_object_agg(p.key, p.value), '{}'::jsonb)
       from node_params p where p.node_id = n.id) as params,
    (select coalesce(jsonb_agg(jsonb_build_object('to', e.to_node, 'rel', e.relation)), '[]'::jsonb)
       from edges e where e.from_node = n.id) as children,
    (select coalesce(jsonb_agg(jsonb_build_object('from', e.from_node, 'rel', e.relation)), '[]'::jsonb)
       from edges e where e.to_node = n.id) as parents
from nodes n
left join node_status s on s.node_id = n.id;

-- ============================================================
-- RLS — keep simple: service_role only (the worker/web use SUPABASE_SERVICE_KEY)
-- Anon access is fully blocked by default since RLS is enabled but no policies exist.
-- ============================================================
alter table events            enable row level security;
alter table trades            enable row level security;
alter table account_snapshots enable row level security;
alter table pending_signals   enable row level security;
alter table nodes             enable row level security;
alter table edges             enable row level security;
alter table node_params       enable row level security;
alter table node_status       enable row level security;
alter table decisions         enable row level security;
