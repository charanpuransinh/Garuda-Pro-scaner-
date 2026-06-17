import { useState, useMemo, useCallback } from "react";
import { AreaChart, Area, XAxis, YAxis, Tooltip, ReferenceLine, ResponsiveContainer } from "recharts";

// ── Black-Scholes ─────────────────────────────────────────────────────────────
function erf(x){const a1=0.254829592,a2=-0.284496736,a3=1.421413741,a4=-1.453152027,a5=1.061405429,p=0.3275911;const sign=x<0?-1:1;x=Math.abs(x);const t=1/(1+p*x);return sign*(1-(((((a5*t+a4)*t)+a3)*t+a2)*t+a1)*t*Math.exp(-x*x));}
function N(x){return 0.5*(1+erf(x/Math.sqrt(2)));}
function nPDF(x){return Math.exp(-0.5*x*x)/Math.sqrt(2*Math.PI);}
function bs(S,K,T,r,sig,type){
  if(T<=0){const i=type==="call"?Math.max(S-K,0):Math.max(K-S,0);return{price:i,delta:type==="call"?(S>K?1:0):(S<K?-1:0),gamma:0,theta:0,vega:0};}
  const d1=(Math.log(S/K)+(r+0.5*sig*sig)*T)/(sig*Math.sqrt(T)),d2=d1-sig*Math.sqrt(T);
  const price=type==="call"?S*N(d1)-K*Math.exp(-r*T)*N(d2):K*Math.exp(-r*T)*N(-d2)-S*N(-d1);
  const delta=type==="call"?N(d1):N(d1)-1;
  const gamma=nPDF(d1)/(S*sig*Math.sqrt(T));
  const theta=type==="call"?(-(S*nPDF(d1)*sig)/(2*Math.sqrt(T))-r*K*Math.exp(-r*T)*N(d2))/365:(-(S*nPDF(d1)*sig)/(2*Math.sqrt(T))+r*K*Math.exp(-r*T)*N(-d2))/365;
  const vega=S*nPDF(d1)*Math.sqrt(T)/100;
  return{price:Math.max(0,price),delta,gamma,theta,vega};
}

// ── INDICES ───────────────────────────────────────────────────────────────────
const INDICES = {
  NIFTY:     {label:"NIFTY 50",    lot:75,   color:"#58a6ff", spot:22500},
  BANKNIFTY: {label:"BANK NIFTY",  lot:15,   color:"#ffd700", spot:48000},
  SENSEX:    {label:"SENSEX",      lot:10,   color:"#ff7043", spot:74000},
  FINNIFTY:  {label:"FIN NIFTY",   lot:40,   color:"#bc8cff", spot:21000},
};

// ── Strategy Engine ───────────────────────────────────────────────────────────
function evalStrategy(id, {spot,strike,iv,days,pcr,oiTrend,prem,lots,lotSize,callG,putG}){
  const mult=lots*lotSize;
  const T=days/365, r=0.065, sig=iv/100;
  const atmCall=bs(spot,strike,T,r,sig,"call");
  const atmPut =bs(spot,strike,T,r,sig,"put");
  const otmCall=bs(spot,strike*1.005,T,r,sig,"call");
  const otmPut =bs(spot,strike*0.995,T,r,sig,"put");

  // shared helpers
  const ivLow=iv<18, ivMed=iv>=18&&iv<=30, ivHigh=iv>30;
  const bullish=oiTrend==="bullish", bearish=oiTrend==="bearish", sideways=oiTrend==="sideways";
  const pcrBull=pcr>1.2, pcrBear=pcr<0.8, pcrNeutral=pcr>=0.8&&pcr<=1.2;
  const expiryDay=days<=1;
  const highGamma=atmCall.gamma>0.0005;

  switch(id){
    case "expiry_gamma": {
      // Expiry Gamma Scalp — buy ATM Call or Put on expiry day
      let score=0, dir="call";
      if(expiryDay) score+=3; else if(days<=2) score+=1;
      if(ivLow) score+=2;
      if(highGamma) score+=2;
      if(bullish&&pcrBull){score+=2;dir="call";}
      else if(bearish&&pcrBear){score+=2;dir="put";}
      else score-=1;
      const g=bs(spot,strike,T,r,sig,dir);
      const pnlFn=s=>(bs(s,strike,0,r,sig,dir).price-prem)*mult;
      const signal=score>=6?"🚀 STRONG BUY":score>=4?"✅ BUY":score>=2?"⚠️ WAIT":"❌ AVOID";
      const scolor=score>=6?"#00e676":score>=4?"#69f0ae":score>=2?"#ffd740":"#f44336";
      return{
        signal,scolor,dir:dir.toUpperCase(),
        entry:`₹${prem}`,
        target:`₹${(prem*2.5).toFixed(0)}`,
        sl:`₹${(prem*0.4).toFixed(0)}`,
        maxProfit:`₹${(prem*2.5*mult).toFixed(0)}`,
        maxLoss:`-₹${(prem*mult).toFixed(0)}`,
        be:`₹${dir==="call"?strike+prem:strike-prem}`,
        checks:[
          {q:"Expiry Day है?", ok:expiryDay, y:"✅ हाँ — Gamma ज़्यादा", n:"⚠️ Expiry अभी दूर"},
          {q:"IV कम है?",       ok:ivLow,    y:"✅ सस्ता मिलेगा",       n:"⚠️ महँगा है"},
          {q:"Direction Clear?",ok:bullish||bearish, y:"✅ Trend है",    n:"⚠️ Sideways मत लो"},
          {q:"PCR Confirm?",    ok:pcrBull||pcrBear, y:"✅ PCR साथ है", n:"⚠️ PCR Mixed"},
        ],
        note:"Expiry पर ATM option 15-30 min hold करो। Gamma बहुत तेज़ — जल्दी निकलो।",
        pnlFn
      };
    }

    case "expiry_short": {
      // Expiry Short Straddle — sell ATM Call+Put
      let score=0;
      if(expiryDay) score+=3; else if(days<=2) score+=1;
      if(ivHigh||ivMed) score+=2;
      if(sideways||pcrNeutral) score+=2;
      if(!bullish&&!bearish) score+=1;
      const premium2=atmCall.price+atmPut.price;
      const pnlFn=s=>(prem-(Math.max(s-strike,0)+Math.max(strike-s,0)))*mult;
      const signal=score>=6?"🚀 STRONG SELL":score>=4?"✅ SELL":score>=2?"⚠️ WAIT":"❌ AVOID";
      const scolor=score>=6?"#00e676":score>=4?"#69f0ae":score>=2?"#ffd740":"#f44336";
      return{
        signal,scolor,dir:"SELL CALL+PUT",
        entry:`₹${(atmCall.price+atmPut.price).toFixed(0)} (combined)`,
        target:`₹${(prem*0.5).toFixed(0)} (50% decay)`,
        sl:`₹${(prem*1.5).toFixed(0)} combined`,
        maxProfit:`₹${(prem*mult).toFixed(0)}`,
        maxLoss:`Unlimited ⚠️`,
        be:`₹${strike-prem} — ₹${strike+prem}`,
        checks:[
          {q:"Expiry Day है?",    ok:expiryDay, y:"✅ Theta ज़्यादा",       n:"⚠️ Theta कम"},
          {q:"IV High है?",       ok:ivHigh||ivMed, y:"✅ Premium ज़्यादा",  n:"⚠️ IV कम — कमाई कम"},
          {q:"Sideways Market?",  ok:sideways||pcrNeutral, y:"✅ Range bound",n:"⚠️ Trend है — मत करो"},
          {q:"OI दोनों Side High?",ok:!bullish&&!bearish, y:"✅ Balance है", n:"⚠️ एक Side ज़्यादा"},
        ],
        note:"बेचने के बाद 3:15 तक रखो। बाज़ार एक direction में जाए तो तुरंत SL।",
        pnlFn
      };
    }

    case "scalp_momentum": {
      // Scalping — Momentum Delta Play (5-15 min)
      let score=0, dir="call";
      if(iv<25) score+=2;
      if(atmCall.delta>0.45) score+=2;
      if(atmCall.gamma>0.0003) score+=2;
      if(bullish&&pcrBull){score+=3;dir="call";}
      else if(bearish&&pcrBear){score+=3;dir="put";}
      else score-=2;
      if(days>1) score+=1;
      const pnlFn=s=>(bs(s,strike,T,r,sig,dir).price-prem)*mult;
      const signal=score>=7?"🚀 SCALP NOW":score>=4?"✅ GOOD SETUP":score>=2?"⚠️ WAIT":"❌ SKIP";
      const scolor=score>=7?"#00e676":score>=4?"#69f0ae":score>=2?"#ffd740":"#f44336";
      return{
        signal,scolor,dir:`${dir.toUpperCase()} SCALP`,
        entry:`₹${prem}`,
        target:`₹${(prem*1.3).toFixed(0)} (30%)`,
        sl:`₹${(prem*0.8).toFixed(0)} (20%)`,
        maxProfit:`₹${(prem*0.3*mult).toFixed(0)}`,
        maxLoss:`-₹${(prem*0.2*mult).toFixed(0)}`,
        be:`₹${dir==="call"?strike+prem:strike-prem}`,
        checks:[
          {q:"Strong Trend है?",   ok:bullish||bearish, y:"✅ Direction Clear", n:"❌ Sideways में मत"},
          {q:"Delta > 0.45?",      ok:atmCall.delta>0.45, y:"✅ Fast move मिलेगा",n:"⚠️ Slow"},
          {q:"Gamma अच्छा है?",    ok:atmCall.gamma>0.0003, y:"✅ Quick gain",   n:"⚠️ Slow"},
          {q:"PCR साथ है?",        ok:pcrBull||pcrBear, y:"✅ Confirm",          n:"⚠️ Mixed"},
        ],
        note:"5-15 मिनट trade। 30% profit मिलते ही निकलो। Loss 20% से ज़्यादा नहीं।",
        pnlFn
      };
    }

    case "scalp_reversal": {
      // Scalping — Reversal at Key Level
      let score=0, dir="call";
      const nearSupport=Math.abs(spot-strike)<spot*0.003;
      if(nearSupport) score+=3;
      if(atmPut.delta<-0.6&&bearish){score+=2;dir="put";}
      else if(atmCall.delta>0.6&&bullish){score+=2;dir="call";}
      if(ivLow) score+=1;
      if(pcrBull&&dir==="call") score+=2;
      if(pcrBear&&dir==="put") score+=2;
      const pnlFn=s=>(bs(s,strike,T,r,sig,dir).price-prem)*mult;
      const signal=score>=6?"🚀 REVERSAL BUY":score>=4?"✅ GOOD":score>=2?"⚠️ RISKY":"❌ SKIP";
      const scolor=score>=6?"#00e676":score>=4?"#69f0ae":score>=2?"#ffd740":"#f44336";
      return{
        signal,scolor,dir:`${dir.toUpperCase()} REVERSAL`,
        entry:`₹${prem}`,
        target:`₹${(prem*1.5).toFixed(0)} (50%)`,
        sl:`₹${(prem*0.7).toFixed(0)} (30%)`,
        maxProfit:`₹${(prem*0.5*mult).toFixed(0)}`,
        maxLoss:`-₹${(prem*0.3*mult).toFixed(0)}`,
        be:`₹${dir==="call"?strike+prem:strike-prem}`,
        checks:[
          {q:"Key Level पर है?",   ok:nearSupport, y:"✅ Support/Resistance पर",n:"⚠️ बीच में है"},
          {q:"Delta Strong?",      ok:Math.abs(dir==="call"?atmCall.delta:atmPut.delta)>0.5, y:"✅ अच्छा",n:"⚠️ Weak"},
          {q:"PCR Reversal?",      ok:pcrBull||pcrBear, y:"✅ Signal है",      n:"⚠️ Mixed"},
          {q:"IV Affordable?",     ok:!ivHigh, y:"✅ ठीक है",                  n:"⚠️ महँगा"},
        ],
        note:"Support/Resistance से reversal पर trade। Strict SL रखो।",
        pnlFn
      };
    }

    case "intraday_spread": {
      // Intraday Bull/Bear Call Spread
      let score=0, dir="bull";
      if(bullish&&pcrBull){score+=3;dir="bull";}
      else if(bearish&&pcrBear){score+=3;dir="bear";}
      else score-=1;
      if(ivHigh||ivMed) score+=2;
      if(days>=1) score+=1;
      if(Math.abs(atmCall.delta)>0.4) score+=1;
      const spreadCost=dir==="bull"?atmCall.price-otmCall.price:atmPut.price-otmPut.price;
      const pnlFn=dir==="bull"
        ?s=>(Math.max(s-strike,0)-Math.max(s-strike*1.005,0)-spreadCost)*mult
        :s=>(Math.max(strike-s,0)-Math.max(strike*0.995-s,0)-spreadCost)*mult;
      const signal=score>=5?"✅ SPREAD KARO":score>=3?"⚠️ POSSIBLE":"❌ AVOID";
      const scolor=score>=5?"#69f0ae":score>=3?"#ffd740":"#f44336";
      return{
        signal,scolor,dir:dir==="bull"?"BULL CALL SPREAD":"BEAR PUT SPREAD",
        entry:`₹${spreadCost.toFixed(0)} (net cost)`,
        target:`₹${(spreadCost*2).toFixed(0)}`,
        sl:`₹${(spreadCost*0.5).toFixed(0)}`,
        maxProfit:`₹${(strike*0.005*mult).toFixed(0)}`,
        maxLoss:`-₹${(spreadCost*mult).toFixed(0)}`,
        be:`₹${dir==="bull"?(strike+spreadCost).toFixed(0):(strike-spreadCost).toFixed(0)}`,
        checks:[
          {q:"Trend Clear?",    ok:bullish||bearish, y:"✅ Direction है",   n:"⚠️ Sideways"},
          {q:"IV ज़्यादा है?", ok:ivHigh||ivMed,    y:"✅ Spread सस्ता",   n:"⚠️ Spread महँगा"},
          {q:"Delta OK?",       ok:Math.abs(atmCall.delta)>0.4, y:"✅ Move होगा",n:"⚠️ Weak"},
          {q:"PCR साथ है?",    ok:pcrBull||pcrBear, y:"✅ Confirm",         n:"⚠️ Mixed"},
        ],
        note:"IV ज़्यादा हो तो Spread सबसे अच्छा — कम risk, defined loss। 3:15 तक ज़रूर निकलो।",
        pnlFn
      };
    }

    case "intraday_atm": {
      // Intraday Directional ATM Buy
      let score=0, dir="call";
      if(bullish&&pcrBull){score+=3;dir="call";}
      else if(bearish&&pcrBear){score+=3;dir="put";}
      if(ivLow) score+=2; else if(ivMed) score+=1;
      if(atmCall.vega>0.2) score+=1;
      if(Math.abs(atmCall.delta)>0.45) score+=2;
      if(Math.abs(atmCall.theta)<15) score+=1;
      const pnlFn=s=>(bs(s,strike,T,r,sig,dir).price-prem)*mult;
      const signal=score>=7?"🚀 STRONG BUY":score>=5?"✅ BUY":score>=3?"⚠️ WAIT":"❌ AVOID";
      const scolor=score>=7?"#00e676":score>=5?"#69f0ae":score>=3?"#ffd740":"#f44336";
      return{
        signal,scolor,dir:`ATM ${dir.toUpperCase()} BUY`,
        entry:`₹${prem}`,
        target:`₹${(prem*2).toFixed(0)} (100%)`,
        sl:`₹${(prem*0.5).toFixed(0)} (50%)`,
        maxProfit:`₹${(prem*mult).toFixed(0)}`,
        maxLoss:`-₹${(prem*mult).toFixed(0)}`,
        be:`₹${dir==="call"?strike+prem:strike-prem}`,
        checks:[
          {q:"Direction Clear?",ok:bullish||bearish, y:"✅ Trend है",         n:"❌ Sideways — मत लो"},
          {q:"IV कम है?",       ok:ivLow||ivMed,    y:"✅ Theta कम",          n:"⚠️ Decay ज़्यादा"},
          {q:"Delta > 0.45?",   ok:Math.abs(atmCall.delta)>0.45,y:"✅ Good", n:"⚠️ OTM है — slow"},
          {q:"Vega OK?",        ok:atmCall.vega>0.2, y:"✅ IV बढ़ी तो फ़ायदा",n:"⚠️ Vega कम"},
        ],
        note:"ATM option intraday की जान है। 50% SL strict रखो। 12 बजे के बाद Theta ज़्यादा।",
        pnlFn
      };
    }

    default: return null;
  }
}

// ── AI Box ────────────────────────────────────────────────────────────────────
function AIBox({inputs}){
  const [resp,setResp]=useState("");
  const [loading,setLoading]=useState(false);

  const ask=useCallback(async()=>{
    setLoading(true); setResp("");
    const prompt=`तुम एक expert options trader हो जो हिंदी में बात करते हो।

मेरे inputs:
- Index: ${inputs.indexName}
- Spot Price: ₹${inputs.spot}
- Strike: ₹${inputs.strike}
- IV: ${inputs.iv}%
- Days to Expiry: ${inputs.days}
- PCR: ${inputs.pcr}
- OI Trend: ${inputs.oiTrend}
- Premium: ₹${inputs.prem}
- Lots: ${inputs.lots}
- Delta (Call): ${inputs.delta?.toFixed(3)}
- Gamma: ${inputs.gamma?.toFixed(5)}
- Theta: ${inputs.theta?.toFixed(2)}
- Vega: ${inputs.vega?.toFixed(3)}

इन सब को मिलाकर मुझे बताओ:
1. अभी कौन सी एक best strategy लूँ?
2. Entry, Target, Stop Loss क्या रहेगा?
3. क्या कोई risk है?
4. एक लाइन में final advice।

हिंदी में, simple भाषा में, 150 words से कम में बताओ।`;

    try{
      const res=await fetch("https://api.anthropic.com/v1/messages",{
        method:"POST",
        headers:{"Content-Type":"application/json"},
        body:JSON.stringify({
          model:"claude-sonnet-4-20250514",
          max_tokens:1000,
          messages:[{role:"user",content:prompt}]
        })
      });
      const data=await res.json();
      setResp(data.content?.map(c=>c.text||"").join("")||"Error");
    }catch(e){setResp("Error: "+e.message);}
    setLoading(false);
  },[inputs]);

  return(
    <div style={{background:"linear-gradient(135deg,#0d2a1a,#1a0d2a)",border:"1px solid #3fb95066",
      borderRadius:14,padding:"16px",marginBottom:14}}>
      <div style={{display:"flex",justifyContent:"space-between",alignItems:"center",marginBottom:10}}>
        <div>
          <div style={{fontSize:10,letterSpacing:3,color:"#3fb950",fontWeight:700}}>🤖 AI ADVISOR</div>
          <div style={{color:"#e6edf3",fontSize:13,fontWeight:700,marginTop:2}}>Claude AI Analysis</div>
          <div style={{color:"#8b949e",fontSize:10}}>सब Greeks+OI+PCR मिलाकर advice</div>
        </div>
        <button onClick={ask} disabled={loading} style={{
          background:loading?"#21262d":"#3fb950",color:loading?"#8b949e":"#010409",
          border:"none",borderRadius:8,padding:"10px 16px",cursor:loading?"not-allowed":"pointer",
          fontWeight:700,fontSize:12,fontFamily:"monospace",transition:"all 0.2s"
        }}>{loading?"⏳ सोच रहा हूँ...":"🧠 AI से पूछो"}</button>
      </div>
      {resp&&(
        <div style={{background:"#0d1117",borderRadius:10,padding:"14px",
          borderLeft:"3px solid #3fb950",marginTop:8}}>
          <div style={{color:"#c9d1d9",fontSize:13,lineHeight:1.8,whiteSpace:"pre-wrap"}}>{resp}</div>
        </div>
      )}
      {!resp&&!loading&&(
        <div style={{color:"#484f58",fontSize:11,textAlign:"center",padding:"10px 0"}}>
          ऊपर inputs भरो और "AI से पूछो" दबाओ — हिंदी में advice मिलेगी
        </div>
      )}
    </div>
  );
}

// ── P&L Mini Chart ─────────────────────────────────────────────────────────────
function MiniChart({pnlFn,spot,color}){
  const data=useMemo(()=>{
    const r=spot*0.06, pts=[];
    for(let s=spot-r;s<=spot+r;s+=r/20)
      pts.push({p:Math.round(s),v:parseFloat(pnlFn(s).toFixed(0))});
    return pts;
  },[pnlFn,spot]);
  return(
    <ResponsiveContainer width="100%" height={80}>
      <AreaChart data={data} margin={{top:2,right:2,left:2,bottom:2}}>
        <defs><linearGradient id={`mg${color.replace("#","")}`} x1="0" y1="0" x2="0" y2="1">
          <stop offset="5%" stopColor={color} stopOpacity={0.3}/>
          <stop offset="95%" stopColor={color} stopOpacity={0.02}/>
        </linearGradient></defs>
        <XAxis dataKey="p" hide/>
        <YAxis hide/>
        <Tooltip formatter={(v)=>`₹${v}`} labelFormatter={(l)=>`₹${l}`}
          contentStyle={{background:"#0d1117",border:`1px solid ${color}`,borderRadius:6,fontSize:10}}/>
        <ReferenceLine y={0} stroke="#30363d" strokeDasharray="2 2"/>
        <ReferenceLine x={spot} stroke={color} strokeDasharray="2 2"/>
        <Area type="monotone" dataKey="v" stroke={color} strokeWidth={1.5}
          fill={`url(#mg${color.replace("#","")})`} dot={false}/>
      </AreaChart>
    </ResponsiveContainer>
  );
}

// ── Strategy Card ─────────────────────────────────────────────────────────────
function StratCard({title, badge, badgeColor, emoji, result, spot, collapsed, onToggle}){
  if(!result) return null;
  const {signal,scolor,dir,entry,target,sl,maxProfit,maxLoss,be,checks,note,pnlFn}=result;
  return(
    <div style={{background:"#161b22",border:`1px solid ${scolor}44`,borderRadius:12,
      overflow:"hidden",marginBottom:12}}>
      {/* Header */}
      <div onClick={onToggle} style={{padding:"12px 14px",cursor:"pointer",
        display:"flex",justifyContent:"space-between",alignItems:"center",
        background:`${scolor}08`}}>
        <div style={{display:"flex",gap:10,alignItems:"center"}}>
          <span style={{fontSize:22}}>{emoji}</span>
          <div>
            <div style={{display:"flex",gap:6,alignItems:"center"}}>
              <span style={{color:"#e6edf3",fontWeight:700,fontSize:13}}>{title}</span>
              <span style={{background:`${badgeColor}22`,color:badgeColor,fontSize:9,
                padding:"2px 7px",borderRadius:20,fontWeight:700}}>{badge}</span>
            </div>
            <div style={{color:"#8b949e",fontSize:10,marginTop:1}}>{dir}</div>
          </div>
        </div>
        <div style={{textAlign:"right"}}>
          <div style={{color:scolor,fontWeight:700,fontSize:12}}>{signal}</div>
          <div style={{color:"#484f58",fontSize:10,marginTop:2}}>{collapsed?"▼ खोलो":"▲ बंद करो"}</div>
        </div>
      </div>

      {/* Body */}
      {!collapsed&&(
        <div style={{padding:"12px 14px"}}>
          {/* Key Numbers */}
          <div style={{display:"grid",gridTemplateColumns:"repeat(3,1fr)",gap:6,marginBottom:10}}>
            {[
              {l:"Entry",v:entry,c:"#58a6ff"},
              {l:"Target 🎯",v:target,c:"#00e676"},
              {l:"Stop Loss 🛑",v:sl,c:"#f44336"},
              {l:"Max Profit",v:maxProfit,c:"#00e676"},
              {l:"Max Loss",v:maxLoss,c:"#f44336"},
              {l:"Breakeven",v:be,c:"#ffd740"},
            ].map(i=>(
              <div key={i.l} style={{background:"#0d1117",borderRadius:7,padding:"7px 8px",textAlign:"center"}}>
                <div style={{color:"#8b949e",fontSize:9}}>{i.l}</div>
                <div style={{color:i.c,fontWeight:700,fontSize:11,marginTop:2}}>{i.v}</div>
              </div>
            ))}
          </div>

          {/* Mini Chart */}
          <div style={{background:"#0d1117",borderRadius:8,padding:"6px",marginBottom:10}}>
            <div style={{color:"#484f58",fontSize:9,marginBottom:2,paddingLeft:4}}>P&L at Expiry</div>
            <MiniChart pnlFn={pnlFn} spot={spot} color={scolor}/>
          </div>

          {/* Checklist */}
          <div style={{marginBottom:10}}>
            {checks.map((c,i)=>(
              <div key={i} style={{display:"flex",justifyContent:"space-between",
                padding:"5px 0",borderBottom:"1px solid #21262d"}}>
                <span style={{color:"#8b949e",fontSize:11}}>{c.q}</span>
                <span style={{color:c.ok?"#00e676":"#ffa657",fontSize:11,fontWeight:700}}>
                  {c.ok?c.y:c.n}
                </span>
              </div>
            ))}
          </div>

          {/* Note */}
          <div style={{background:`${scolor}0d`,border:`1px solid ${scolor}33`,
            borderRadius:8,padding:"8px 10px"}}>
            <div style={{color:scolor,fontSize:11}}>💡 {note}</div>
          </div>
        </div>
      )}
    </div>
  );
}

// ── MAIN APP ──────────────────────────────────────────────────────────────────
export default function App(){
  const [idx,setIdx]     = useState("NIFTY");
  const [spot,setSpot]   = useState(22500);
  const [strike,setStr]  = useState(22500);
  const [iv,setIv]       = useState(15);
  const [days,setDays]   = useState(7);
  const [pcr,setPcr]     = useState(1.1);
  const [oiTrend,setOI]  = useState("bullish");
  const [prem,setPrem]   = useState(150);
  const [lots,setLots]   = useState(1);
  const [open,setOpen]   = useState({
    expiry_gamma:true, expiry_short:true,
    scalp_momentum:true, scalp_reversal:true,
    intraday_spread:true, intraday_atm:true
  });

  const inst=INDICES[idx];
  const lotSize=inst.lot;
  const T=days/365, r=0.065, sig=iv/100;
  const callG=useMemo(()=>bs(spot,strike,T,r,sig,"call"),[spot,strike,T,r,sig]);
  const putG =useMemo(()=>bs(spot,strike,T,r,sig,"put"), [spot,strike,T,r,sig]);

  const inputs={spot,strike,iv,days,pcr,oiTrend,prem,lots,lotSize,callG,putG};
  const aiInputs={indexName:inst.label,spot,strike,iv,days,pcr,oiTrend,prem,lots,
    delta:callG.delta,gamma:callG.gamma,theta:callG.theta,vega:callG.vega};

  const toggle=id=>setOpen(p=>({...p,[id]:!p[id]}));

  const strategies=[
    {id:"expiry_gamma",  title:"Expiry Gamma Scalp",  badge:"EXPIRY",  badgeColor:"#f44336", emoji:"⚡"},
    {id:"expiry_short",  title:"Expiry Short Straddle",badge:"EXPIRY",  badgeColor:"#f44336", emoji:"🏦"},
    {id:"scalp_momentum",title:"Momentum Scalp",      badge:"SCALPING",badgeColor:"#ffd700", emoji:"🔥"},
    {id:"scalp_reversal",title:"Reversal Scalp",      badge:"SCALPING",badgeColor:"#ffd700", emoji:"↩️"},
    {id:"intraday_spread",title:"Bull/Bear Spread",   badge:"INTRADAY",badgeColor:"#58a6ff", emoji:"📊"},
    {id:"intraday_atm",  title:"ATM Directional Buy", badge:"INTRADAY",badgeColor:"#58a6ff", emoji:"🎯"},
  ];

  const inp={background:"#0d1117",border:"1px solid #30363d",color:"#e6edf3",
    borderRadius:8,padding:"9px 10px",width:"100%",fontSize:13,
    outline:"none",fontFamily:"monospace",boxSizing:"border-box"};
  const lbl={color:"#8b949e",fontSize:10,letterSpacing:1,fontWeight:700,marginBottom:4,display:"block"};

  return(
    <div style={{minHeight:"100vh",background:"#010409",color:"#e6edf3",
      fontFamily:"monospace",padding:"14px 12px 60px",
      backgroundImage:`radial-gradient(ellipse at 15% 0%,${inst.color}15 0%,transparent 50%),
                       radial-gradient(ellipse at 85% 80%,#1a0d2a 0%,transparent 50%)`}}>

      {/* Header */}
      <div style={{textAlign:"center",marginBottom:16}}>
        <div style={{fontSize:9,letterSpacing:4,color:inst.color,marginBottom:5}}>🇮🇳 OPTION STRATEGY SCANNER</div>
        <h1 style={{margin:0,fontSize:19,fontWeight:700}}>6 Strategy + AI Advisor</h1>
        <p style={{color:"#8b949e",fontSize:11,margin:"4px 0 0"}}>
          Expiry · Scalping · Intraday · Greeks · PCR · OI
        </p>
      </div>

      {/* Index Selector */}
      <div style={{display:"grid",gridTemplateColumns:"repeat(4,1fr)",gap:6,marginBottom:14}}>
        {Object.entries(INDICES).map(([k,v])=>(
          <button key={k} onClick={()=>{setIdx(k);setSpot(v.spot);setStr(v.spot);}} style={{
            padding:"9px 4px",border:`1px solid ${idx===k?v.color:"#21262d"}`,
            borderRadius:8,background:idx===k?`${v.color}18`:"#161b22",cursor:"pointer",
            transition:"all 0.2s",boxShadow:idx===k?`0 0 10px ${v.color}33`:"none"
          }}>
            <div style={{color:idx===k?v.color:"#8b949e",fontWeight:700,fontSize:11}}>{k}</div>
            <div style={{color:"#484f58",fontSize:9,marginTop:1}}>Lot:{v.lot}</div>
          </button>
        ))}
      </div>

      {/* Common Inputs */}
      <div style={{background:"#161b22",border:`1px solid ${inst.color}33`,
        borderRadius:12,padding:"14px",marginBottom:14}}>
        <div style={{color:"#8b949e",fontSize:10,letterSpacing:2,marginBottom:10}}>
          ⚙️ INPUTS — एक बार भरो, सभी strategies update होंगी
        </div>
        <div style={{display:"grid",gridTemplateColumns:"1fr 1fr",gap:8}}>
          {[
            ["Spot Price ₹",spot,setSpot,"अभी का भाव"],
            ["Strike Price ₹",strike,setStr,"कौन सा Strike?"],
            ["IV % (Volatility)",iv,setIv,"15=कम, 35=ज़्यादा"],
            ["Days to Expiry",days,setDays,"Expiry दिन"],
            ["PCR Value",pcr,setPcr,">1.2=Bull, <0.8=Bear"],
            ["Premium ₹",prem,setPrem,"Option का भाव"],
            ["Lots",lots,setLots,"कितने Lots?"],
          ].map(([label,val,setter,hint])=>(
            <div key={label}>
              <label style={lbl}>{label}</label>
              <input type="number" value={val}
                onChange={e=>setter(parseFloat(e.target.value)||0)} style={inp}/>
              <div style={{color:"#484f58",fontSize:9,marginTop:2}}>{hint}</div>
            </div>
          ))}
          <div>
            <label style={lbl}>OI Trend</label>
            <select value={oiTrend} onChange={e=>setOI(e.target.value)} style={inp}>
              <option value="bullish">🟢 Bullish</option>
              <option value="bearish">🔴 Bearish</option>
              <option value="sideways">🟡 Sideways</option>
            </select>
          </div>
        </div>
      </div>

      {/* Greeks Live Display */}
      <div style={{background:"#161b22",border:"1px solid #21262d",borderRadius:12,
        padding:"12px 14px",marginBottom:14}}>
        <div style={{color:"#8b949e",fontSize:10,letterSpacing:2,marginBottom:8}}>📐 LIVE GREEKS (Call ATM)</div>
        <div style={{display:"grid",gridTemplateColumns:"repeat(4,1fr)",gap:6}}>
          {[
            {n:"Δ DELTA",v:callG.delta.toFixed(3),c:"#58a6ff",
             ok:callG.delta>0.45,y:"Strong",n2:"Weak"},
            {n:"γ GAMMA",v:callG.gamma.toFixed(5),c:"#bc8cff",
             ok:callG.gamma>0.0003,y:"High",n2:"Low"},
            {n:"θ THETA",v:`-${Math.abs(callG.theta).toFixed(1)}`,c:"#f85149",
             ok:Math.abs(callG.theta)<10,y:"Cheap",n2:"Costly"},
            {n:"ν VEGA",v:callG.vega.toFixed(3),c:"#ffa657",
             ok:iv<25,y:"Buy IV",n2:"Sell IV"},
          ].map(g=>(
            <div key={g.n} style={{textAlign:"center",background:"#0d1117",borderRadius:8,padding:"8px 4px"}}>
              <div style={{color:g.c,fontSize:9,fontWeight:700}}>{g.n}</div>
              <div style={{color:"#e6edf3",fontSize:14,fontWeight:700,margin:"3px 0"}}>{g.v}</div>
              <div style={{color:g.ok?"#00e676":"#f44336",fontSize:9}}>{g.ok?g.y:g.n2}</div>
            </div>
          ))}
        </div>
        {/* PCR + OI visual */}
        <div style={{display:"grid",gridTemplateColumns:"1fr 1fr",gap:6,marginTop:8}}>
          <div style={{background:"#0d1117",borderRadius:8,padding:"8px 10px",
            display:"flex",justifyContent:"space-between",alignItems:"center"}}>
            <span style={{color:"#8b949e",fontSize:11}}>PCR</span>
            <span style={{color:pcr>1.2?"#00e676":pcr<0.8?"#f44336":"#ffd740",fontWeight:700,fontSize:13}}>
              {pcr.toFixed(2)} {pcr>1.2?"🟢 Bullish":pcr<0.8?"🔴 Bearish":"🟡 Neutral"}
            </span>
          </div>
          <div style={{background:"#0d1117",borderRadius:8,padding:"8px 10px",
            display:"flex",justifyContent:"space-between",alignItems:"center"}}>
            <span style={{color:"#8b949e",fontSize:11}}>OI Trend</span>
            <span style={{color:oiTrend==="bullish"?"#00e676":oiTrend==="bearish"?"#f44336":"#ffd740",
              fontWeight:700,fontSize:13}}>
              {oiTrend==="bullish"?"🟢 Bullish":oiTrend==="bearish"?"🔴 Bearish":"🟡 Sideways"}
            </span>
          </div>
        </div>
      </div>

      {/* ── AI BOX ── */}
      <AIBox inputs={aiInputs}/>

      {/* ── 6 STRATEGY CARDS ── */}
      <div style={{color:"#8b949e",fontSize:10,letterSpacing:2,marginBottom:10}}>
        ⚡ STRATEGIES — tap to expand/collapse
      </div>

      {strategies.map(s=>{
        const result=evalStrategy(s.id,inputs);
        return(
          <StratCard key={s.id}
            title={s.title} badge={s.badge} badgeColor={s.badgeColor}
            emoji={s.emoji} result={result} spot={spot}
            collapsed={open[s.id]} onToggle={()=>toggle(s.id)}/>
        );
      })}

      {/* Footer */}
      <div style={{textAlign:"center",color:"#484f58",fontSize:10,marginTop:10,lineHeight:1.9}}>
        ⚠️ Educational Tool Only · हमेशा Stop Loss लगाएँ<br/>
        Paper Trading पहले · Capital का 5% से ज़्यादा एक trade में नहीं
      </div>
    </div>
  );
}
