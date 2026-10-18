-- Exact-time clock for the automation (18 Oct 2026).
--
-- GitHub starts scheduled workflows hours late or not at all (the engine's
-- 12:30 IST run started at 17:24 IST on 18 Oct 2026). The website's price
-- fetch already runs on time from this Supabase clock
-- (Taazabhav-website: db/morning-trigger.sql); this file adds the
-- automation repo to it, reusing the same GitHub token from the vault.
--
--   Content engine   A 07:30 IST, D 12:30, C 18:30, B 20:30  (mode "auto")
--   Telegram channel 13:00 IST, again 16:00 IST (posts once a day)
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
select cron.schedule('taazabhav-auto-engine-a', '0 2 * * *',
  $$select public.dispatch_automation('engine.yml', '{"series":"A","mode":"auto"}')$$);
select cron.schedule('taazabhav-auto-engine-d', '0 7 * * *',
  $$select public.dispatch_automation('engine.yml', '{"series":"D","mode":"auto"}')$$);
select cron.schedule('taazabhav-auto-engine-c', '0 13 * * *',
  $$select public.dispatch_automation('engine.yml', '{"series":"C","mode":"auto"}')$$);
select cron.schedule('taazabhav-auto-engine-b', '0 15 * * *',
  $$select public.dispatch_automation('engine.yml', '{"series":"B","mode":"auto"}')$$);
select cron.schedule('taazabhav-auto-telegram', '30 7,10 * * *',
  $$select public.dispatch_automation('telegram_daily.yml')$$);

-- Test now: starts the Telegram broadcast once (it posts at most once a day).
select public.dispatch_automation('telegram_daily.yml');
