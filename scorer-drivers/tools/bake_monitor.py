#!/usr/bin/env python3
"""Bake SCORER-MONITOR.html from the AUTHORITATIVE node endpoints.

The old bake_dashboard.py read /addresses/<wallet>, which is cached and undercounts (it
showed 38/45 while the wallet actually held 44). The source of truth is the per-intent
endpoint /intents/<keccak256(name)> -> the active scorer, cross-checked against
/wasm/<regid> for the author, margin and win counts. This script resolves every one of our
intents that way, bakes the result into a self-contained page, and also writes each intent's
keccak id into the page so the browser can refresh live over http without a keccak library.

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
    """Authoritative holder + margins for one intent."""
    d = get(f"{NODE}/intents/{kec(intent)}")
    ws = (d or {}).get("wasm", [])
    active = [s for s in ws if str(s.get("status", "")).lower() == "active"]
    row = {"intent": intent, "id": kec(intent), "held": False, "holder": "none",
           "regid": None, "margin": None, "champ": None, "wins": None,
           "cases": None, "gate": None}
    if active:
        rid = active[0].get("registration_id")
        w = (get(f"{NODE}/wasm/{rid}") or {}).get("wasm", {})
        e = evd(w)
        addr = str(w.get("AuthorAddress", "")).lower()
        row.update(regid=rid, holder=("US" if addr == OURL else w.get("AuthorAddress", "")[:10]),
                   held=(addr == OURL), margin=e.get("candidate_margin"),
                   wins=e.get("candidate_wins"), cases=e.get("comparable_cases"),
                   gate=("traffic" if (e.get("historical_rows_evaluated") or 0) > 0 else "separation"))
    return row
# BUILD


TEMPLATE = r"""<!DOCTYPE html>
<meta charset="utf-8">
<title>Telegraph scorer monitor</title>
<style>
  :root{--ink:#14171c;--dim:#5b6472;--line:#e4e8ef;--accent:#1c6ea4;--bg:#fbfaf8;--ok:#1c7a43;--bad:#b21f1f}
  *{box-sizing:border-box}
  body{margin:0;padding:28px 20px 70px;background:var(--bg);color:var(--ink);font:14px/1.55 ui-sans-serif,-apple-system,"Segoe UI",Roboto,sans-serif}
  main{max-width:1000px;margin:0 auto}
  h1{font-size:20px;margin:0 0 2px;letter-spacing:-.01em}
  .sub{color:var(--dim);font-size:12px;margin:0 0 16px}
  .bar{display:flex;gap:16px;align-items:center;flex-wrap:wrap;background:#fff;border:1px solid var(--line);border-radius:10px;padding:14px 16px;margin:0 0 16px}
  .big{font-size:30px;font-weight:800;letter-spacing:-.02em}
  .big .den{color:var(--dim);font-weight:600;font-size:18px}
  .pill{font:600 11px/1 ui-sans-serif;padding:5px 9px;border-radius:999px;border:1px solid var(--line)}
  .pill.ok{background:#e7f6ee;color:var(--ok);border-color:#bfe6cf}
  .pill.bad{background:#fdeaea;color:var(--bad);border-color:#f2c9c9}
  button{font:600 12px/1 ui-sans-serif;padding:8px 13px;border-radius:6px;border:1px solid var(--ink);background:var(--ink);color:#fff;cursor:pointer}
  button:disabled{opacity:.5;cursor:default}
  table{width:100%;border-collapse:collapse;background:#fff;border:1px solid var(--line);border-radius:10px;overflow:hidden;margin:0 0 18px}
  th,td{text-align:left;padding:8px 12px;border-bottom:1px solid var(--line);font-size:13px}
  th{font-size:11px;text-transform:uppercase;letter-spacing:.08em;color:var(--dim);background:#f7f8fa}
  td.num{font:12px ui-monospace,monospace;text-align:right}
  tr:last-child td{border-bottom:none}
  .tag{font:600 10px/1 ui-monospace;padding:3px 6px;border-radius:4px}
  .held{background:#e7f6ee;color:var(--ok)} .lost{background:#fdeaea;color:var(--bad)}
  .g{color:var(--dim);font-size:11px}
  h2{font-size:12px;text-transform:uppercase;letter-spacing:.12em;color:var(--accent);margin:22px 0 8px}
  code{font:12px ui-monospace;background:#f2f3f6;padding:1px 4px;border-radius:3px}
  .note{color:var(--dim);font-size:12px;margin:6px 0 0}
</style>
<main>
  <h1>Telegraph scorer monitor</h1>
  <p class="sub">Wallet <code id="wallet"></code> · source of truth is the per-intent endpoint, not the cached address list</p>
  <div class="bar">
    <div><span class="big" id="stat"></span></div>
    <span class="pill" id="minerpill"></span>
    <span class="g" id="gen"></span>
    <button id="refresh">Refresh from node</button>
    <span class="g" id="rstatus"></span>
  </div>
  <h2>Intents</h2>
  <table id="itbl"><thead><tr><th>Intent</th><th>Status</th><th>Holder</th><th>Gate</th><th class="num">Our / champ margin</th><th class="num">Wins</th><th class="num">reg</th></tr></thead><tbody id="itbody"></tbody></table>
  <h2>Miners</h2>
  <table id="mtbl"><thead><tr><th>Intent</th><th>Slug</th><th>Status</th><th class="num">reg</th></tr></thead><tbody id="mbody"></tbody></table>
  <p class="note">Baked snapshot renders offline (file://). <b>Refresh from node</b> works when served over http (browsers block cross-origin fetch from file://). Rebake the snapshot with <code>python3 tools/bake_monitor.py</code>.</p>
</main>
<script>
const SNAP = /*SNAP*/;
const NODE = SNAP.node;
const OURL = SNAP.wallet.toLowerCase();
const $ = id => document.getElementById(id);
const m4 = v => (v==null?'-':(+v).toFixed(4));

function paintStat(){
  const held = SNAP.rows.filter(r=>r.held).length;
  $('stat').innerHTML = held + '<span class="den">/' + SNAP.total + ' held</span>';
  $('minerpill').className = 'pill ' + (SNAP.minersActive===SNAP.miners.length?'ok':'');
  $('minerpill').textContent = SNAP.minersActive + '/' + SNAP.miners.length + ' miners active';
  $('gen').textContent = 'snapshot ' + SNAP.generated;
  $('wallet').textContent = SNAP.wallet;
}
function rowHTML(r){
  const tag = r.held ? '<span class="tag held">HELD</span>' : '<span class="tag lost">LOST</span>';
  const holder = r.held ? 'us' : (r.holder||'?');
  return '<tr>'+
    '<td>'+r.intent+'</td>'+
    '<td>'+tag+'</td>'+
    '<td class="g">'+holder+'</td>'+
    '<td class="g">'+(r.gate||'-')+'</td>'+
    '<td class="num">'+m4(r.margin)+'</td>'+
    '<td class="num">'+(r.wins==null?'-':r.wins)+(r.cases?('/'+r.cases):'')+'</td>'+
    '<td class="num g">'+(r.regid||'-')+'</td>'+
  '</tr>';
}
function render(){
  paintStat();
  const rows = SNAP.rows.slice().sort((a,b)=>(a.held-b.held)|| a.intent.localeCompare(b.intent));
  $('itbody').innerHTML = rows.map(rowHTML).join('');
  $('mbody').innerHTML = SNAP.miners.map(m=>'<tr><td>'+(m.intent||'-')+'</td><td class="g">'+m.slug+'</td><td>'+
    (m.status==='active'?'<span class="tag held">ACTIVE</span>':'<span class="tag lost">'+(m.status||'?').toUpperCase()+'</span>')+
    '</td><td class="num g">'+(m.reg||'-')+'</td></tr>').join('');
}
async function jget(u){const r=await fetch(u,{cache:'no-store'});return r.json();}
async function refresh(){
  const btn=$('refresh'); btn.disabled=true;
  const st=$('rstatus'); let done=0;
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
        r.gate=(e.historical_rows_evaluated>0)?'traffic':'separation';
      } else { r.held=false; r.holder='none'; }
    }catch(err){ /* leave row as-is on a fetch error */ }
    done++; st.textContent='checked '+done+'/'+SNAP.rows.length; render();
  }
  SNAP.generated=new Date().toISOString().slice(0,16).replace('T',' ')+' UTC (live)';
  render(); st.textContent='done, '+SNAP.rows.filter(r=>r.held).length+'/'+SNAP.total+' held'; btn.disabled=false;
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
    # miners: best (active first) per slug
    mb = {}
    for m in addr.get("miners", []):
        s = m.get("Slug") or m.get("MinerSlug") or m.get("slug")
        if s not in mb or str(m.get("ActivationStatus", "")).lower() == "active":
            mb[s] = m
    miners = [{"slug": s, "intent": m.get("IntentID"),
               "status": str(m.get("ActivationStatus", "")).lower(),
               "reg": m.get("RegistrationID")} for s, m in mb.items() if s]
    miners.sort(key=lambda x: x["intent"] or "")
    snap = {"generated": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
            "wallet": WALLET, "node": NODE, "held": held, "total": len(rows),
            "rows": sorted(rows, key=lambda r: (r["held"], r["intent"])),
            "miners": miners,
            "minersActive": sum(1 for m in miners if m["status"] == "active")}
    html = TEMPLATE.replace("/*SNAP*/", json.dumps(snap))
    open(OUT, "w").write(html)
    print(f"baked {held}/{len(rows)} held at {snap['generated']}")
    lost = [r["intent"] for r in rows if not r["held"]]
    print("not held:", lost or "none (45/45)")


if __name__ == "__main__":
    main()

