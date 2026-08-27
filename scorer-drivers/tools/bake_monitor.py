#!/usr/bin/env python3
"""Bake SCORER-MONITOR.html from the AUTHORITATIVE node endpoints.

Scorers come from the per-intent endpoint /intents/<keccak256(name)> -> the active scorer,
cross-checked against /wasm/<regid> for the author, margin, wins and the traffic rows it has
graded. Miners come from /api/miners, which carries each miner's live rank, canonical score
and total requests served. The page bakes a snapshot that renders offline and refreshes both
tables live when served over http.

    python3 tools/bake_monitor.py
"""
import json, os, subprocess, time
from datetime import datetime, timezone
from Crypto.Hash import keccak

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "..", "SCORER-MONITOR.html")
WALLET = "0x8b224783FE5b3c52B7DB0cb9B1754f8812b75287"
OURL = WALLET.lower()
NODE = "https://devnode.telegraphprotocol.com/engine/validator/v1"
API_MINERS = "https://devnode.telegraphprotocol.com/api/miners"


def get(url):
    for _ in range(3):
        r = subprocess.run(["curl", "-s", "--max-time", "20", url], capture_output=True, text=True)
        try:
            return json.loads(r.stdout)
        except Exception:
            time.sleep(2)
    return None


def kec(s):
    h = keccak.new(digest_bits=256)
    h.update(s.encode())
    return h.hexdigest()


def evd(w):
    try:
        return json.loads(w["EvalDetails"]) if w.get("EvalDetails") else {}
    except Exception:
        return {}


def resolve(intent):
    """Authoritative holder, margins and graded-traffic count for one intent's scorer."""
    d = get(f"{NODE}/intents/{kec(intent)}")
    ws = (d or {}).get("wasm", [])
    active = [s for s in ws if str(s.get("status", "")).lower() == "active"]
    row = {"intent": intent, "id": kec(intent), "held": False, "holder": "none",
           "regid": None, "margin": None, "champ": None, "wins": None,
           "cases": None, "served": None, "gate": None}
    if active:
        rid = active[0].get("registration_id")
        w = (get(f"{NODE}/wasm/{rid}") or {}).get("wasm", {})
        e = evd(w)
        addr = str(w.get("AuthorAddress", "")).lower()
        row.update(regid=rid, holder=("US" if addr == OURL else w.get("AuthorAddress", "")[:10]),
                   held=(addr == OURL), margin=e.get("candidate_margin"),
                   wins=e.get("candidate_wins"), cases=e.get("comparable_cases"),
                   served=e.get("historical_rows_evaluated"),
                   gate=("traffic" if (e.get("historical_rows_evaluated") or 0) > 0 else "separation"))
    return row


def our_miners():
    """Our miners from /api/miners: per-intent rank, canonical score and requests served."""
    api = get(API_MINERS) or []
    rows = api if isinstance(api, list) else api.get("miners", [])
    out = []
    for m in rows:
        if str(m.get("wallet_address", "")).lower() != OURL:
            continue
        intents = m.get("supported_intents") or []
        primary = intents[0] if intents else None
        scores = m.get("scores") or []
        pick = next((s for s in scores if s.get("intent_id") == primary), scores[0] if scores else {})
        out.append({
            "slug": m.get("slug"), "intent": primary,
            "status": str(m.get("activation_status", "")).lower(),
            "rank": pick.get("rank"), "score": pick.get("score"),
            "epoch": pick.get("epoch_id"),
            "served": m.get("total_requests_served"),
            "reg": m.get("id"),
        })
    out.sort(key=lambda x: (x["intent"] or "", x["slug"] or ""))
    return out

# __TEMPLATE__


TEMPLATE = r"""<!DOCTYPE html>
<meta charset="utf-8">
<title>Telegraph scorer and miner monitor</title>
<style>
  :root{--ink:#14171c;--dim:#5b6472;--line:#e4e8ef;--accent:#1c6ea4;--bg:#fbfaf8;--ok:#1c7a43;--bad:#b21f1f;--gold:#a5720b}
  *{box-sizing:border-box}
  body{margin:0;padding:28px 20px 70px;background:var(--bg);color:var(--ink);font:14px/1.55 ui-sans-serif,-apple-system,"Segoe UI",Roboto,sans-serif}
  main{max-width:1040px;margin:0 auto}
  h1{font-size:20px;margin:0 0 2px;letter-spacing:-.01em}
  .sub{color:var(--dim);font-size:12px;margin:0 0 16px}
  .bar{display:flex;gap:16px;align-items:center;flex-wrap:wrap;background:#fff;border:1px solid var(--line);border-radius:10px;padding:14px 16px;margin:0 0 16px}
  .big{font-size:30px;font-weight:800;letter-spacing:-.02em}
  .big .den{color:var(--dim);font-weight:600;font-size:18px}
  .pill{font:600 11px/1 ui-sans-serif;padding:5px 9px;border-radius:999px;border:1px solid var(--line)}
  .pill.ok{background:#e7f6ee;color:var(--ok);border-color:#bfe6cf}
  button{font:600 12px/1 ui-sans-serif;padding:8px 13px;border-radius:6px;border:1px solid var(--ink);background:var(--ink);color:#fff;cursor:pointer}
  button:disabled{opacity:.5;cursor:default}
  table{width:100%;border-collapse:collapse;background:#fff;border:1px solid var(--line);border-radius:10px;overflow:hidden;margin:0 0 18px}
  th,td{text-align:left;padding:8px 12px;border-bottom:1px solid var(--line);font-size:13px}
  th{font-size:11px;text-transform:uppercase;letter-spacing:.08em;color:var(--dim);background:#f7f8fa;cursor:pointer}
  td.num{font:12px ui-monospace,monospace;text-align:right}
  tr:last-child td{border-bottom:none}
  .tag{font:600 10px/1 ui-monospace;padding:3px 6px;border-radius:4px}
  .held{background:#e7f6ee;color:var(--ok)} .lost{background:#fdeaea;color:var(--bad)}
  .r1{color:var(--gold);font-weight:800} .g{color:var(--dim);font-size:11px}
  h2{font-size:12px;text-transform:uppercase;letter-spacing:.12em;color:var(--accent);margin:22px 0 8px}
  code{font:12px ui-monospace;background:#f2f3f6;padding:1px 4px;border-radius:3px}
  .note{color:var(--dim);font-size:12px;margin:6px 0 0}
</style>
<main>
  <h1>Telegraph scorer and miner monitor</h1>
  <p class="sub">Wallet <code id="wallet"></code> · scorers from the per-intent endpoint, miners from <code>/api/miners</code>, both authoritative</p>
  <div class="bar">
    <div><span class="big" id="stat"></span></div>
    <span class="pill" id="minerpill"></span>
    <span class="pill" id="throne"></span>
    <span class="g" id="gen"></span>
    <button id="refresh">Refresh from node</button>
    <span class="g" id="rstatus"></span>
  </div>
  <h2>Scorers we hold (the judges)</h2>
  <table id="itbl"><thead><tr><th>Intent</th><th>Status</th><th>Holder</th><th>Gate</th><th class="num">Our / margin</th><th class="num">Wins</th><th class="num">Traffic scored</th><th class="num">reg</th></tr></thead><tbody id="itbody"></tbody></table>
  <h2>Our miners (the answerers)</h2>
  <table id="mtbl"><thead><tr><th>Intent</th><th>Slug</th><th>Status</th><th class="num">Rank</th><th class="num">Score</th><th class="num">Requests served</th><th class="num">reg</th></tr></thead><tbody id="mbody"></tbody></table>
  <p class="note">Baked snapshot renders offline (file://). <b>Refresh from node</b> works when served over http (browsers block cross-origin fetch from file://): <code>python3 -m http.server</code> in this folder, then open the page from localhost. Rebake with <code>python3 scorer/tools/bake_monitor.py</code>. "Traffic scored" is the real traffic rows a scorer has graded; "Requests served" is the answers a miner has returned.</p>
</main>
<script>
const SNAP = /*SNAP*/;
const NODE = SNAP.node, API = SNAP.apiMiners, OURL = SNAP.wallet.toLowerCase();
const $ = id => document.getElementById(id);
const m4 = v => (v==null?'-':(+v).toFixed(4));
const rankCell = r => (r==null?'-':(r===1?'<span class="r1">#1</span>':'#'+r));
// __SCRIPT2__
function paintStat(){
  const held = SNAP.rows.filter(r=>r.held).length;
  $('stat').innerHTML = held + '<span class="den">/' + SNAP.total + ' scorers held</span>';
  $('minerpill').className = 'pill ' + (SNAP.minersActive===SNAP.miners.length?'ok':'');
  $('minerpill').textContent = SNAP.minersActive + '/' + SNAP.miners.length + ' miners active';
  const thrones = SNAP.miners.filter(m=>m.rank===1).length;
  $('throne').className = 'pill ' + (thrones?'ok':'');
  $('throne').textContent = thrones + ' miner' + (thrones===1?'':'s') + ' at rank 1';
  $('gen').textContent = 'snapshot ' + SNAP.generated;
  $('wallet').textContent = SNAP.wallet;
}
function scorerRow(r){
  const tag = r.held ? '<span class="tag held">HELD</span>' : '<span class="tag lost">LOST</span>';
  return '<tr>'+
    '<td>'+r.intent+'</td>'+
    '<td>'+tag+'</td>'+
    '<td class="g">'+(r.held?'us':(r.holder||'?'))+'</td>'+
    '<td class="g">'+(r.gate||'-')+'</td>'+
    '<td class="num">'+m4(r.margin)+'</td>'+
    '<td class="num">'+(r.wins==null?'-':r.wins)+(r.cases?('/'+r.cases):'')+'</td>'+
    '<td class="num">'+(r.served==null?'-':r.served)+'</td>'+
    '<td class="num g">'+(r.regid||'-')+'</td>'+
  '</tr>';
}
function minerRow(m){
  const st = m.status==='active'?'<span class="tag held">ACTIVE</span>':'<span class="tag lost">'+(m.status||'?').toUpperCase()+'</span>';
  return '<tr>'+
    '<td>'+(m.intent||'-')+'</td>'+
    '<td class="g">'+m.slug+'</td>'+
    '<td>'+st+'</td>'+
    '<td class="num">'+rankCell(m.rank)+'</td>'+
    '<td class="num">'+m4(m.score)+'</td>'+
    '<td class="num">'+(m.served==null?0:m.served)+'</td>'+
    '<td class="num g">'+(m.reg||'-')+'</td>'+
  '</tr>';
}
function render(){
  paintStat();
  const rows = SNAP.rows.slice().sort((a,b)=>(a.held-b.held)|| a.intent.localeCompare(b.intent));
  $('itbody').innerHTML = rows.map(scorerRow).join('');
  const ms = SNAP.miners.slice().sort((a,b)=>((a.rank||99)-(b.rank||99))|| (a.intent||'').localeCompare(b.intent||''));
  $('mbody').innerHTML = ms.map(minerRow).join('');
}
async function jget(u){const r=await fetch(u,{cache:'no-store'});return r.json();}
async function refreshScorers(st){
  let done=0;
  for(const r of SNAP.rows){
    try{
      const d=await jget(NODE+'/intents/'+r.id);
      const act=(d.wasm||[]).filter(s=>String(s.status||'').toLowerCase()==='active');
      if(act.length){
        const w=(await jget(NODE+'/wasm/'+act[0].registration_id)).wasm||{};
        let e={}; try{e=JSON.parse(w.EvalDetails||'{}')}catch(_){}
        const addr=String(w.AuthorAddress||'').toLowerCase();
        r.held=addr===OURL; r.holder=r.held?'US':(w.AuthorAddress||'').slice(0,10);
        r.regid=w.RegistrationID; r.margin=e.candidate_margin;
        r.wins=e.candidate_wins; r.cases=e.comparable_cases;
        r.served=e.historical_rows_evaluated;
        r.gate=(e.historical_rows_evaluated>0)?'traffic':'separation';
      } else { r.held=false; r.holder='none'; }
    }catch(err){ /* leave row as-is */ }
    done++; st.textContent='scorers '+done+'/'+SNAP.rows.length; render();
  }
}
async function refreshMiners(st){
  try{
    const api=await jget(API);
    const rows=Array.isArray(api)?api:(api.miners||[]);
    const mine=rows.filter(m=>String(m.wallet_address||'').toLowerCase()===OURL);
    const by={}; for(const m of mine) by[m.slug]=m;
    for(const cur of SNAP.miners){
      const m=by[cur.slug]; if(!m) continue;
      const ints=m.supported_intents||[]; const primary=cur.intent||ints[0];
      const sc=(m.scores||[]); const pick=sc.find(s=>s.intent_id===primary)||sc[0]||{};
      cur.status=String(m.activation_status||'').toLowerCase();
      cur.rank=pick.rank; cur.score=pick.score; cur.served=m.total_requests_served;
    }
    SNAP.minersActive=SNAP.miners.filter(m=>m.status==='active').length;
    st.textContent='miners updated';
  }catch(err){ st.textContent='miner refresh failed'; }
  render();
}
async function refresh(){
  const btn=$('refresh'); btn.disabled=true; const st=$('rstatus');
  await refreshScorers(st);
  await refreshMiners(st);
  SNAP.generated=new Date().toISOString().slice(0,16).replace('T',' ')+' UTC (live)';
  render();
  st.textContent='done, '+SNAP.rows.filter(r=>r.held).length+'/'+SNAP.total+' scorers held, '+SNAP.miners.filter(m=>m.rank===1).length+' at rank 1';
  btn.disabled=false;
}
$('refresh').addEventListener('click',refresh);
render();
</script>
"""


def main():
    addr = get(f"{NODE}/addresses/{WALLET}")
    if not addr:
        raise SystemExit("node unreachable")
    intents = sorted({s["IntentID"] for s in addr.get("wasm", [])})
    rows = [resolve(it) for it in intents]
    held = sum(1 for r in rows if r["held"])
    miners = our_miners()
    snap = {"generated": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
            "wallet": WALLET, "node": NODE, "apiMiners": API_MINERS,
            "held": held, "total": len(rows),
            "rows": sorted(rows, key=lambda r: (r["held"], r["intent"])),
            "miners": miners,
            "minersActive": sum(1 for m in miners if m["status"] == "active")}
    html = TEMPLATE.replace("/*SNAP*/", json.dumps(snap))
    open(OUT, "w").write(html)
    thrones = sum(1 for m in miners if m.get("rank") == 1)
    print(f"baked {held}/{len(rows)} scorers held, {len(miners)} miners ({thrones} at rank 1) at {snap['generated']}")
    lost = [r["intent"] for r in rows if not r["held"]]
    print("scorers not held:", lost or "none (45/45)")
    for m in miners:
        print(f"  miner {m['slug']:26} {str(m['intent']):22} rank {m['rank']} score {m['score']} served {m['served']}")


if __name__ == "__main__":
    main()
