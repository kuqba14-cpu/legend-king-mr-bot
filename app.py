import os, requests
from flask import Flask, jsonify, request, render_template_string
from dotenv import load_dotenv

load_dotenv()
app = Flask(__name__)
KEY = os.getenv("TWELVE_DATA_API_KEY")

HTML = """<!doctype html><html><head>
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>LEGEND KING MR BOT</title>
<style>
body{margin:0;background:#050708;color:#eee;font-family:Arial;padding:15px}
h1{color:#ffd84a}.tabs{display:flex;gap:8px}.tabs button{flex:1;padding:14px;background:#111;color:#ffd84a;border:1px solid #806719;border-radius:10px}
.card{margin:12px 0;padding:18px;border:1px solid #383019;border-radius:16px;background:#090b0c}
.sig{font-size:28px;font-weight:bold;margin:15px 0}.CALL{color:#00d69b}.PUT{color:#ff5757}.WAIT{color:#d8b72e}
small{color:#888}.err{color:#ff7777;margin-top:20px}
</style></head><body>
<h1>👑 LEGEND KING MR BOT</h1><small>LIVE NORMAL FOREX · 1M / 5M</small>
<p><button onclick="load(1)">1 MIN</button> <button onclick="load(5)">5 MIN</button></p>
<div id="out">Loading...</div>
<script>
async function load(tf){out.innerHTML='Loading live data...';try{
let r=await fetch('/api/live?timeframe='+tf),d=await r.json();
if(d.error) throw Error(d.error);
out.innerHTML=d.map(x=>`<div class="card"><b>${x.pair}</b><small> · ${x.timeframe} MIN</small>
<div class="sig ${x.signal}">${x.signal}</div><small>Model score: ${x.confidence}%</small>
<p>${x.reasons.join(' · ')}</p></div>`).join('');
}catch(e){out.innerHTML='<div class="err">'+e.message+'</div>'}}
load(5); setInterval(()=>load(5),60000);
</script></body></html>"""

def ema(v,p):
    if len(v)<p:return None
    k=2/(p+1); x=sum(v[:p])/p
    for n in v[p:]: x=n*k+x*(1-k)
    return x
def rsi(v,p=14):
    if len(v)<p+1:return 50
    g=[];l=[]
    for a,b in zip(v[-p-1:-1],v[-p:]):
        d=b-a;g.append(max(d,0));l.append(max(-d,0))
    ag=sum(g)/p;al=sum(l)/p
    return 100 if al==0 else 100-100/(1+ag/al)

@app.get("/")
def home(): return render_template_string(HTML)

@app.get("/api/live")
def live():
    if not KEY:return jsonify({"error":"API key is not configured on Render yet."}),400
    tf=int(request.args.get("timeframe",5))
    pairs=["EUR/USD","GBP/USD","USD/JPY","AUD/USD","USD/CAD","EUR/GBP"]
    result=[]
    for pair in pairs:
        try:
            d=requests.get("https://api.twelvedata.com/time_series",
                params={"symbol":pair,"interval":f"{tf}min","outputsize":60,"apikey":KEY},timeout=15).json()
            vals=list(reversed(d.get("values",[])))
            if len(vals)<30: continue
            c=[float(x["close"]) for x in vals]
            e9,e21=ema(c,9),ema(c,21); rr=rsi(c)
            call=put=0; why=[]
            if e9>e21: call+=30;why.append("EMA UP")
            else: put+=30;why.append("EMA DOWN")
            if 52<=rr<=68: call+=25;why.append("RSI UP")
            elif 32<=rr<=48: put+=25;why.append("RSI DOWN")
            if c[-1]>c[-3]: call+=20;why.append("Momentum UP")
            elif c[-1]<c[-3]: put+=20;why.append("Momentum DOWN")
            if c[-1]>float(vals[-1]["open"]): call+=15
            elif c[-1]<float(vals[-1]["open"]): put+=15
            sig="CALL" if call>=55 and call>put else "PUT" if put>=55 and put>call else "WAIT"
            score=max(call,put)
            result.append({"pair":pair,"timeframe":tf,"signal":sig,"confidence":score,"reasons":why})
        except Exception: pass
    return jsonify(result)

if __name__=="__main__":
    app.run(host="0.0.0.0",port=10000)
