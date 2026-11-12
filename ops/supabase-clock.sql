-- Exact-time clock for the automation (18 Oct 2026).
--
-- GitHub starts scheduled workflows hours late or not at all (the engine's
-- 12:30 IST run started at 17:24 IST on 18 Oct 2026). The website's price
-- fetch already runs on time from this Supabase clock
-- (Taazabhav-website: db/morning-trigger.sql); this file adds the
-- automation repo to it, reusing the same GitHub token from the vault.
--
--   Content engine   D/Y 12:30 IST, B 20:30  (mode "auto"; A and C stopped 3 Nov 2026)
--   Telegram channel 13:00 IST, again 16:00 IST (posts once a day)
--   FB/IG posts 07:30 / 09:30 / 14:30 / 18:30 IST and the 17:00 MP Kisan Kalyan Reel (12 Nov 2026)
--
-- The workflows' own GitHub schedules stay as late backups; each one runs
-- once per slot (engine/slot_gate.py, data/telegram_history/_last_post.json)
-- and tells the owner on Telegram when this clock missed a slot.
--
-- One-time setup:
--   1. GitHub → Settings → Developer settings → Fine-grained tokens → the
--      token used for the morning price fetch → Edit → Repository access:
--      add taazabhav-automation (keep Taazabhav-website). Permissions stay
--      "Actions: Read and write". Save. The token text does not change.
--   2. Supabase dashboard → SQL Editor → paste this whole file → Run.
--      Running it again is safe: it replaces the jobs instead of adding copies.
--
-- Check: select jobname, schedule from cron.job where jobname like 'taazabhav-auto%';
--        select * from net._http_response order by created desc limit 5;  (status 204 = started)
-- Turn one off: select cron.unschedule('taazabhav-auto-engine-a');

create extension if not exists pg_cron;
create extension if not exists pg_net;

create or replace function public.dispatch_automation(workflow text, inputs jsonb default '{}'::jsonb)
returns void
language plpgsql
security definer
set search_path = public
as $$
declare
  tok text;
begin
  select decrypted_secret into tok from vault.decrypted_secrets where name = 'github_dispatch_token';
  if tok is null or tok = 'PASTE_GITHUB_TOKEN_HERE' then
    raise warning 'dispatch_automation: no GitHub token in vault';
    return;
  end if;
  perform net.http_post(
    url := 'https://api.github.com/repos/ny9813136114/taazabhav-automation/actions/workflows/' || workflow || '/dispatches',
    headers := jsonb_build_object(
      'Authorization', 'Bearer ' || tok,
      'Accept', 'application/vnd.github+json',
      'X-GitHub-Api-Version', '2022-11-28',
      'User-Agent', 'taazabhav-automation-clock'),
    body := jsonb_build_object('ref', 'main', 'inputs', inputs));
end $$;

-- Only the scheduler may call it, never the website's public API.
revoke execute on function public.dispatch_automation(text, jsonb) from public, anon, authenticated;

-- pg_cron runs in UTC (IST = UTC + 5:30).
-- A (07:30 bhav) stopped 3 Nov 2026: select cron.unschedule('taazabhav-auto-engine-a');
select cron.schedule('taazabhav-auto-engine-d', '0 7 * * *',
  $$select public.dispatch_automation('engine.yml', '{"series":"D","mode":"auto"}')$$);
-- C (18:30 bhav news) stopped 3 Nov 2026: select cron.unschedule('taazabhav-auto-engine-c');
select cron.schedule('taazabhav-auto-engine-b', '0 15 * * *',
  $$select public.dispatch_automation('engine.yml', '{"series":"B","mode":"auto"}')$$);
select cron.schedule('taazabhav-auto-telegram', '30 7,10 * * *',
  $$select public.dispatch_automation('telegram_daily.yml')$$);

-- 12 Nov 2026: GitHub's own schedule ran the 09:30 tool post at 17:00 IST and the 18:30 yojana
-- carousel at 01:25 IST the day before. These start the FB/IG posts on time; each workflow runs
-- once per slot (engine/slot_gate.py), so GitHub's late backup cannot post them twice.
select cron.schedule('taazabhav-auto-engine-m', '30 11 * * *',
  $$select public.dispatch_automation('engine.yml', '{"series":"M","mode":"auto"}')$$);   -- 17:00 IST MP Kisan Kalyan Reel
select cron.schedule('taazabhav-auto-yojana-am', '0 2 * * *',
  $$select public.dispatch_automation('yojana_posts.yml', '{"slot":"am","mode":"auto"}')$$);  -- 07:30 IST
select cron.schedule('taazabhav-auto-tool-post', '0 4 * * *',
  $$select public.dispatch_automation('posts.yml', '{"mode":"auto"}')$$);                      -- 09:30 IST
select cron.schedule('taazabhav-auto-bhav-post', '0 9 * * *',
  $$select public.dispatch_automation('bhav_post.yml', '{"mode":"auto"}')$$);                  -- 14:30 IST
select cron.schedule('taazabhav-auto-yojana-pm', '0 13 * * *',
  $$select public.dispatch_automation('yojana_posts.yml', '{"slot":"pm","mode":"auto"}')$$);  -- 18:30 IST

-- Test now: starts the Telegram broadcast once (it posts at most once a day).
select public.dispatch_automation('telegram_daily.yml');
