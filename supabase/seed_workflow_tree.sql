-- ============================================================
-- FuturesForged Virtual Office — Workflow Tree Seed
-- ============================================================
-- Seeds the tree from memory: strategies, Cowork queue, infra,
-- prop firms, key decisions. Idempotent — safe to re-run.
-- ============================================================

-- ── ROOT ──
insert into nodes (id, title, kind, summary) values
  ('root', 'FuturesForged', 'doc', 'Proprietary algorithmic futures trading platform — NQ + ES')
on conflict (id) do update set title=excluded.title, summary=excluded.summary;

-- ── BRANCHES ──
insert into nodes (id, title, kind, summary) values
  ('branch.strategies', 'Strategies',    'doc', 'Active and queued trading strategies'),
  ('branch.infra',      'Infrastructure', 'doc', 'Deployment, brokers, connectors'),
  ('branch.accounts',   'Accounts',       'doc', 'Live broker + prop firm accounts'),
  ('branch.cowork',     'Cowork Queue',   'doc', 'Handoff items and build sessions'),
  ('branch.docs',       'Methodology',    'doc', 'Strategy development methodology — phases 1-9')
on conflict (id) do update set title=excluded.title, summary=excluded.summary;

insert into edges (from_node, to_node, relation) values
  ('root','branch.strategies','parent_of'),
  ('root','branch.infra','parent_of'),
  ('root','branch.accounts','parent_of'),
  ('root','branch.cowork','parent_of'),
  ('root','branch.docs','parent_of')
on conflict do nothing;

-- ── STRATEGIES ──
insert into nodes (id, title, kind, summary) values
  ('strat.sweep_reverse',   'Sweep & Reverse',          'strategy', 'NY session 13-17 UTC, NQ'),
  ('strat.box_london',      'Box MR — London',          'strategy', 'London 08:00-10:00 UTC, NQ'),
  ('strat.box_power',       'Box MR — Power Hour',      'strategy', 'Power Hour 20:00-21:00 UTC, NQ'),
  ('strat.momentum_nq',     'Momentum Breakout — NQ',   'strategy', 'Trend follow on NQ'),
  ('strat.momentum_es',     'Momentum Breakout — ES',   'strategy', 'Trend follow on ES'),
  ('strat.orb_scalp',       'ORB Scalp (shelved)',      'strategy', 'WR 42.7% / PF 1.12 — needs regime filter')
on conflict (id) do update set title=excluded.title, summary=excluded.summary;

insert into edges (from_node, to_node, relation) values
  ('branch.strategies','strat.sweep_reverse','parent_of'),
  ('branch.strategies','strat.box_london','parent_of'),
  ('branch.strategies','strat.box_power','parent_of'),
  ('branch.strategies','strat.momentum_nq','parent_of'),
  ('branch.strategies','strat.momentum_es','parent_of'),
  ('branch.strategies','strat.orb_scalp','parent_of')
on conflict do nothing;

-- ── STRATEGY STATUS ──
insert into node_status (node_id, status, progress) values
  ('strat.sweep_reverse','live', 100),
  ('strat.box_london',   'live', 100),
  ('strat.box_power',    'live', 100),
  ('strat.momentum_nq',  'live', 100),
  ('strat.momentum_es',  'live', 100),
  ('strat.orb_scalp',    'shelved', 30)
on conflict (node_id) do update set status=excluded.status, progress=excluded.progress, updated_at=now();

-- ── STRATEGY PARAMS ──
insert into node_params (node_id, key, value) values
  ('strat.sweep_reverse','session_utc',  '{"start":13,"end":17}'::jsonb),
  ('strat.box_london',   'session_utc',  '{"start":8,"end":10}'::jsonb),
  ('strat.box_power',    'session_utc',  '{"start":20,"end":21}'::jsonb),
  ('strat.orb_scalp',    'backtest',     '{"wr":0.427,"pf":1.12,"shelved_to":"Q3","reason":"insufficient — needs regime filter"}'::jsonb)
on conflict (node_id, key) do update set value=excluded.value, updated_at=now();

-- ── METHODOLOGY PHASES (1-9) ──
insert into nodes (id, title, kind, summary) values
  ('phase.1',  'Phase 1 — Idea',                       'phase', 'Capture concept + premise'),
  ('phase.2',  'Phase 2 — Hypothesis',                 'phase', 'Falsifiable thesis'),
  ('phase.3',  'Phase 3 — Data acquisition',           'phase', 'Databento NQ 1m, etc.'),
  ('phase.4',  'Phase 4 — In-sample backtest',         'phase', 'PF, WR, MAR'),
  ('phase.5',  'Phase 5 — Costs + slippage',           'phase', 'Realistic execution model'),
  ('phase.6',  'Phase 6 — Parameter robustness',       'phase', 'Plateau, not peaks'),
  ('phase.7',  'Phase 7 — Walk-forward validation',    'phase', 'OOS PF > 1.3, eff > 0.6'),
  ('phase.8',  'Phase 8 — Prop firm compatibility',    'phase', 'Trailing DD survival'),
  ('phase.9',  'Phase 9 — Regime-gated deployment',    'phase', 'Hard DO-NOT-TRADE gates')
on conflict (id) do update set title=excluded.title, summary=excluded.summary;

insert into edges (from_node, to_node, relation) values
  ('branch.docs','phase.1','parent_of'),
  ('phase.1','phase.2','parent_of'),
  ('phase.2','phase.3','parent_of'),
  ('phase.3','phase.4','parent_of'),
  ('phase.4','phase.5','parent_of'),
  ('phase.5','phase.6','parent_of'),
  ('phase.6','phase.7','parent_of'),
  ('phase.7','phase.8','parent_of'),
  ('phase.8','phase.9','parent_of')
on conflict do nothing;

-- ── INFRA ──
insert into nodes (id, title, kind, summary) values
  ('infra.render_bot',     'Render — bot worker',        'infra', 'futuresforged-bot.onrender.com (Background Worker)'),
  ('infra.render_vo_web',  'Render — VO web',            'infra', 'Virtual Office Flask dashboard'),
  ('infra.render_vo_wkr',  'Render — VO worker',         'infra', 'Telegram bot polling worker'),
  ('infra.supabase',       'Supabase',                   'infra', 'Events, trades, snapshots, pending signals, workflow tree'),
  ('infra.telegram',       'Telegram bot',               'infra', 'Alerts + commands. Buttons OFF by default'),
  ('infra.nt_ati',         'NinjaTrader ATI',            'infra', 'Port 36973 — execution path for ALL prop firms'),
  ('infra.tradovate_api',  'Tradovate API',              'infra', 'Personal AMP account only'),
  ('infra.rithmic',        'Rithmic',                    'infra', 'Conformance PASSED 2026-05-05 — prefix fufo:'),
  ('infra.github',         'GitHub repo',                'infra', 'hindsights2020x-spec/futuresforged-bot')
on conflict (id) do update set title=excluded.title, summary=excluded.summary;

insert into edges (from_node, to_node, relation) values
  ('branch.infra','infra.render_bot','parent_of'),
  ('branch.infra','infra.render_vo_web','parent_of'),
  ('branch.infra','infra.render_vo_wkr','parent_of'),
  ('branch.infra','infra.supabase','parent_of'),
  ('branch.infra','infra.telegram','parent_of'),
  ('branch.infra','infra.nt_ati','parent_of'),
  ('branch.infra','infra.tradovate_api','parent_of'),
  ('branch.infra','infra.rithmic','parent_of'),
  ('branch.infra','infra.github','parent_of')
on conflict do nothing;

insert into node_status (node_id, status, progress) values
  ('infra.render_bot',     'live', 100),
  ('infra.render_vo_web',  'active', 10),
  ('infra.render_vo_wkr',  'active', 10),
  ('infra.supabase',       'active', 20),
  ('infra.telegram',       'active', 30),
  ('infra.nt_ati',         'live', 100),
  ('infra.tradovate_api',  'live', 100),
  ('infra.rithmic',        'passed', 100),
  ('infra.github',         'live', 100)
on conflict (node_id) do update set status=excluded.status, progress=excluded.progress, updated_at=now();

-- ── ACCOUNTS ──
insert into nodes (id, title, kind, summary) values
  ('acct.amp_229107',  'AMP #229107',           'account', 'LIVE personal — Rithmic broker'),
  ('acct.mffu',        'MyFundedFutures',       'account', 'Eval in progress — routes via NT8 ATI'),
  ('acct.apex',        'Apex Trader Funding',   'account', 'Pending provisioning')
on conflict (id) do update set title=excluded.title, summary=excluded.summary;

insert into edges (from_node, to_node, relation) values
  ('branch.accounts','acct.amp_229107','parent_of'),
  ('branch.accounts','acct.mffu','parent_of'),
  ('branch.accounts','acct.apex','parent_of')
on conflict do nothing;

insert into node_status (node_id, status, progress) values
  ('acct.amp_229107','live', 100),
  ('acct.mffu',      'active', 60),
  ('acct.apex',      'blocked', 0)
on conflict (node_id) do update set status=excluded.status, progress=excluded.progress, updated_at=now();

update node_status set blocker = 'Pending provisioning from Apex' where node_id = 'acct.apex';

-- ── COWORK QUEUE ──
insert into nodes (id, title, kind, summary) values
  ('cw.6',   'Cowork #6 — built',                    'cowork', 'Completed'),
  ('cw.7',   'Cowork #7 — ready',                    'cowork', 'Queued'),
  ('cw.8a',  'Cowork #8a — ready',                   'cowork', 'Queued'),
  ('cw.9',   'Cowork #9 — ready',                    'cowork', 'Queued'),
  ('cw.11',  'Cowork #11 — NT8 Production Bridge',   'cowork', 'In execution'),
  ('cw.vo',  'Cowork — Virtual Office',              'cowork', 'This build')
on conflict (id) do update set title=excluded.title, summary=excluded.summary;

insert into edges (from_node, to_node, relation) values
  ('branch.cowork','cw.6','parent_of'),
  ('branch.cowork','cw.7','parent_of'),
  ('branch.cowork','cw.8a','parent_of'),
  ('branch.cowork','cw.9','parent_of'),
  ('branch.cowork','cw.11','parent_of'),
  ('branch.cowork','cw.vo','parent_of')
on conflict do nothing;

insert into node_status (node_id, status, progress) values
  ('cw.6',  'done',   100),
  ('cw.7',  'idea',     0),
  ('cw.8a', 'idea',     0),
  ('cw.9',  'idea',     0),
  ('cw.11', 'active',  50),
  ('cw.vo', 'active',  80)
on conflict (node_id) do update set status=excluded.status, progress=excluded.progress, updated_at=now();

-- ── KEY DECISIONS (history capture) ──
insert into decisions (node_id, title, rationale, outcome) values
  ('infra.render_bot',    'Render Background Worker (not Web Service)',
                          'Web Services need an HTTP port bound fast; bot doesn''t bind one. Worker pattern with python render_start.py works.',
                          'chosen'),
  ('strat.orb_scalp',     'Shelve ORB scalp to Q3',
                          'Backtest WR 42.7% / PF 1.12 insufficient. Needs regime filtering.',
                          'deferred'),
  ('infra.nt_ati',        'All prop firms route via NT8 ATI (port 36973)',
                          'Uniform routing, no per-firm rules, no whitelisting. Tradovate API blocked by MFFU.',
                          'chosen'),
  ('infra.telegram',      'Pending-signal approve/reject buttons OFF by default',
                          'Scaffold the data layer now; enable interactive control only when explicitly toggled.',
                          'chosen')
on conflict do nothing;
