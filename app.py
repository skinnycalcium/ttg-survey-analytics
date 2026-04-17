import streamlit as st
import pandas as pd
import json
import re

st.set_page_config(page_title="TTG Survey Analytics", page_icon="📊", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500&display=swap');
html,body,[class*="css"]{font-family:'IBM Plex Sans',sans-serif;}
#MainMenu,footer,header{visibility:hidden;}
[data-testid="stSidebar"]{background-color:#0D1F2D!important;border-right:1px solid rgba(255,255,255,0.06);}
[data-testid="stSidebar"] p,[data-testid="stSidebar"] span,[data-testid="stSidebar"] label,[data-testid="stSidebar"] div{color:rgba(255,255,255,0.75)!important;}
[data-testid="stSidebar"] h1,[data-testid="stSidebar"] h2,[data-testid="stSidebar"] h3{color:#ffffff!important;}
[data-testid="stSidebar"] hr{border-color:rgba(255,255,255,0.08)!important;}
[data-testid="stSidebar"] button{background:rgba(255,255,255,0.06)!important;border:1px solid rgba(255,255,255,0.12)!important;color:rgba(255,255,255,0.6)!important;font-size:12px!important;}
.block-container{padding:2rem 2.5rem!important;max-width:100%!important;}
.stat-grid{display:flex;flex-wrap:wrap;gap:10px;margin:1.25rem 0;}
.stat-card{background:#f5f3f0;border-radius:10px;padding:12px 16px;min-width:110px;flex:1;max-width:180px;}
.stat-card .slabel{font-size:11px;color:#777;margin-bottom:4px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;}
.stat-card .svalue{font-size:26px;font-weight:600;line-height:1.1;}
.stat-card .ssub{font-size:10px;color:#aaa;margin-top:2px;font-family:'IBM Plex Mono',monospace;}
.ct-wrap{background:white;border:1px solid #e8e5e0;border-radius:10px;overflow:hidden;margin-top:12px;}
.ct-table{width:100%;border-collapse:collapse;font-size:13px;}
.ct-table thead tr{background:#f5f3f0;}
.ct-table thead th{padding:9px 12px;text-align:right;font-size:11px;font-weight:600;color:#888;border-bottom:1px solid #e8e5e0;white-space:nowrap;}
.ct-table thead th:first-child{text-align:left;}
.ct-table tbody tr{border-bottom:1px solid #f0ede8;}
.ct-table tbody tr:last-child{border-bottom:none;}
.ct-table tbody tr:hover{background:#faf9f7;}
.ct-table tbody td{padding:9px 12px;color:#1a1a1a;}
.ct-table tbody td:first-child{font-weight:500;}
.ct-table tbody td:not(:first-child){text-align:right;}
.pct-cell{display:flex;align-items:center;justify-content:flex-end;gap:6px;}
.pct-bar{height:6px;border-radius:3px;opacity:0.7;flex-shrink:0;}
.pct-val{font-family:'IBM Plex Mono',monospace;font-size:12px;min-width:42px;text-align:right;}
.n-cell{font-family:'IBM Plex Mono',monospace;font-size:11px;color:#aaa;text-align:right;}
.uns-cell{font-family:'IBM Plex Mono',monospace;font-size:11px;color:#bbb;text-align:right;}
.ct-note{font-size:11px;color:#bbb;margin-top:6px;padding:0 2px;}
.qhdr-col{font-family:'IBM Plex Mono',monospace;font-size:11px;color:#999;margin-bottom:4px;}
.qhdr-title{font-size:22px;font-weight:600;color:#0D1F2D;line-height:1.3;margin-bottom:4px;}
.qhdr-meta{font-size:12px;color:#888;margin-bottom:0;}
</style>
""", unsafe_allow_html=True)

COLORS = ["#C0392B","#2874A6","#7D6608","#1A7A4A","#6C3483","#D35400","#5D6D7E","#2E4057"]
DEMO_CONFIG = {
    "qgeo":{"label":"DMA","values":{"1":"Tampa","2":"Orlando","3":"Miami/FLL","4":"Jacksonville","5":"Ft. Myers","6":"GNV/TLH","7":"PNS/PCB","8":"W. Palm Beach"}},
    "qparty":{"label":"Party","values":{"1":"Republican","2":"Democrat","3":"Unaffiliated"}},
    "qgender":{"label":"Gender","values":{"1":"Male","2":"Female"}},
    "qrace":{"label":"Race","values":{"1":"White","2":"Black","3":"Hispanic","4":"Other"}},
    "qage":{"label":"Age","values":{"1":"18-29","2":"30-44","3":"45-54","4":"55-64","5":"65-74","6":"75+"}},
    "qqideology":{"label":"Ideology","values":{"1":"Very Liberal","2":"Somewhat Liberal","3":"Somewhat Conservative","4":"Very Conservative","5":"Moderate"}},
    "qq24presvote":{"label":"2024 Pres Vote","values":{"1":"Trump","2":"Harris","3":"Other","4":"Didn't Vote"}},
    "qqmaga":{"label":"MAGA ID","values":{"1":"MAGA","2":"Non-MAGA"}},
    "qqmethod":{"label":"Vote Method","values":{"1":"Vote by Mail","2":"Early In-Person","3":"Election Day"}},
    "qvote":{"label":"Vote History","values":{"1":"New Voter","2":"1 of 3","3":"2 of 3","4":"3 of 3"}},
    "qptype":{"label":"Mode","values":{"3":"Landline","4":"Cell","5":"SMS"}},
    "q_lang":{"label":"Language","values":{"1":"Spanish","2":"English"}},
}
META_COLS = {"quniqueid","groupid","api_id","phone","firstname","lastname","regis_date","age","voter_id","address","city","state","zip","st_up_hous","st_lo_hous","cong_dist","ai_county_","vtr_gen16","vtr_gen20","vtr_gen24","cnty_comm","dma_name",*[k.lower() for k in DEMO_CONFIG]}
SKIP = {"98","99"," ",""}

def infer_scale(col, uvals):
    cl = col.lower()
    vs = sorted([v for v in uvals if v not in SKIP], key=lambda x:(int(x) if x.isdigit() else 999))
    n = len(vs); has = lambda v: str(v) in vs
    if cl=="q01" and n==2: return {"1":"Definitely Yes","2":"Probably Yes"}
    if re.match(r"^q0[23]$",cl) and n==4: return {"1":"Strongly Approve","2":"Somewhat Approve","3":"Somewhat Disapprove","4":"Strongly Disapprove","98":"Unsure"}
    if has(6) and re.match(r"^q04",cl): return {"1":"Very Favorable","2":"Somewhat Favorable","3":"Somewhat Unfavorable","4":"Very Unfavorable","5":"No Opinion","6":"Never Heard Of"}
    if re.match(r"^q1[3]",cl) and n==4: return {"1":"Much More Likely","2":"Somewhat More Likely","3":"Somewhat Less Likely","4":"Much Less Likely","98":"Unsure"}
    if n==3 and has(1) and has(2) and has(3) and re.match(r"^q1[0-4]",cl): return {"1":"Republican","2":"Democrat","3":"Independent","98":"Unsure"}
    if cl=="q17" and n==4: return {"1":"A lot","2":"A little","3":"Some","4":"Not at all"}
    if n==2 and has(1) and has(2): return {"1":"Yes","2":"No","98":"Unsure"}
    if n==4 and has(1) and has(4): return {"1":"Strongly Agree","2":"Somewhat Agree","3":"Somewhat Disagree","4":"Strongly Disagree","98":"Unsure"}
    return {}

def detect_questions(df, label_map):
    out = []
    for col in df.columns:
        cl = col.lower()
        if not re.match(r"^q\d",cl) or cl in META_COLS: continue
        uv = set(df[col].dropna().astype(str).str.strip().unique()) - SKIP
        if len(uv) < 2: continue
        out.append({"col":col,"label":label_map.get(cl,label_map.get(col,col)),"values":infer_scale(col,set(df[col].dropna().astype(str).str.strip().unique()))})
    return out

def detect_demos(df):
    cl = {c.lower():c for c in df.columns}
    return {cl[k.lower()]:v for k,v in DEMO_CONFIG.items() if k.lower() in cl}

def get_label(q, val):
    return q["values"].get(str(val), q["values"].get(val, f"Option {val}"))

def compute_overall(df, col):
    vals = sorted([v for v in df[col].dropna().astype(str).str.strip().unique() if v not in SKIP and v not in {"98","99"}], key=lambda x:(int(x) if x.isdigit() else 999))
    n = len(df)
    counts = {v:int((df[col].astype(str).str.strip()==v).sum()) for v in vals}
    unsure = int(df[col].astype(str).str.strip().isin(["98","99"]).sum())
    return {"n":n,"vals":vals,"counts":counts,"pcts":{v:counts[v]/n*100 for v in vals},"unsure":unsure,"unsure_pct":unsure/n*100}

def compute_crosstab(df, q_col, by_col, demo_values, two_way=False):
    q_vals = sorted([v for v in df[q_col].dropna().astype(str).str.strip().unique() if v not in SKIP and v not in {"98","99"}], key=lambda x:(int(x) if x.isdigit() else 999))
    rows = []
    for dk, glabel in demo_values.items():
        grp = df[df[by_col].astype(str).str.strip()==str(dk)]
        if not len(grp): continue
        uns = int(grp[q_col].astype(str).str.strip().isin(["98","99"]).sum())
        counts = {v:int((grp[q_col].astype(str).str.strip()==v).sum()) for v in q_vals}
        tot = sum(counts.values())+uns; dec = sum(counts.values())
        if not tot: continue
        denom = dec if two_way else tot
        rows.append({"group":glabel,"n":tot,"pcts":{v:counts[v]/denom*100 if denom>0 else 0 for v in q_vals},"uns_pct":uns/tot*100 if not two_way else None})
    return rows, q_vals

def extract_labels_from_pdf(pdf_bytes, api_key):
    from anthropic import Anthropic
    import base64
    client = Anthropic(api_key=api_key)
    b64 = base64.standard_b64encode(pdf_bytes).decode("utf-8")
    msg = client.messages.create(model="claude-haiku-4-5-20251001", max_tokens=2000, messages=[{"role":"user","content":[
        {"type":"document","source":{"type":"base64","media_type":"application/pdf","data":b64}},
        {"type":"text","text":'Survey data key. Return ONLY valid JSON, no markdown. Format: {"q01":"Full question text","q02":"Question text"}'}
    ]}])
    return json.loads(msg.content[0].text.strip().replace("```json","").replace("```","").strip())

def stat_cards_html(ov, q):
    html = '<div class="stat-grid">'
    for i,v in enumerate(ov["vals"]):
        html += f'<div class="stat-card"><div class="slabel">{get_label(q,v)}</div><div class="svalue" style="color:{COLORS[i%8]}">{ov["pcts"][v]:.1f}%</div><div class="ssub">n={ov["counts"][v]:,}</div></div>'
    if ov["unsure"]>0:
        html += f'<div class="stat-card"><div class="slabel">Unsure / Refused</div><div class="svalue" style="color:#bbb">{ov["unsure_pct"]:.1f}%</div><div class="ssub">n={ov["unsure"]:,}</div></div>'
    return html + '</div>'

def crosstab_html(rows, q_vals, q, two_way):
    vlabels = [get_label(q,v) for v in q_vals]
    th = '<thead><tr><th style="text-align:left">Group</th><th style="text-align:right;color:#aaa">n</th>'
    for i,lbl in enumerate(vlabels):
        suf = " 2W" if two_way else ""
        th += f'<th style="color:{COLORS[i%8]}">{lbl}{suf}</th>'
    if not two_way: th += '<th style="color:#ccc">Unsure</th>'
    th += '</tr></thead>'
    tb = '<tbody>'
    for row in rows:
        tb += f'<tr><td>{row["group"]}</td><td class="n-cell">{row["n"]}</td>'
        for i,v in enumerate(q_vals):
            pct = row["pcts"].get(v,0); bw = max(2,int(pct*0.5))
            tb += f'<td><div class="pct-cell"><div class="pct-bar" style="width:{bw}px;background:{COLORS[i%8]}"></div><span class="pct-val">{pct:.1f}%</span></div></td>'
        if not two_way: tb += f'<td class="uns-cell">{(row.get("uns_pct") or 0):.1f}%</td>'
        tb += '</tr>'
    tb += '</tbody>'
    note = "decided only — unsure excluded" if two_way else "unsure included in denominator"
    return f'<div class="ct-wrap"><table class="ct-table">{th}{tb}</table></div><div class="ct-note">Pcts ({note})</div>'

def main():
    if "df" not in st.session_state: st.session_state.df = None

    with st.sidebar:
        st.markdown("## TTG Survey Analytics")
        st.markdown("*The Tyson Group · P2 Insights*")
        st.divider()
        if st.session_state.df is not None:
            qs = st.session_state.questions
            st.caption(f"{len(st.session_state.df):,} respondents · {len(qs)} questions")
            st.divider()
            sel_idx = st.radio("Questions", range(len(qs)), format_func=lambda i: f"{qs[i]['col']} — {qs[i]['label']}" if qs[i]['label']!=qs[i]['col'] else qs[i]['col'], label_visibility="collapsed")
            st.divider()
            if st.button("← New survey"):
                for k in ["df","questions","demos","label_map"]: st.session_state.pop(k,None)
                st.rerun()

    if st.session_state.df is None:
        st.markdown('<div style="background:#0D1F2D;padding:2rem;border-radius:12px;margin-bottom:2rem;max-width:600px"><h1 style="color:white;margin:0;font-size:24px;font-family:IBM Plex Sans">TTG Survey Analytics</h1><p style="color:rgba(255,255,255,0.5);margin:6px 0 0;font-size:13px">The Tyson Group · P2 Insights</p></div>', unsafe_allow_html=True)
        with st.container():
            csv_file = st.file_uploader("Survey data CSV", type=["csv"])
            pdf_file = st.file_uploader("Data key PDF (optional — auto-extracts question labels)", type=["pdf"])
            api_key = st.text_input("Anthropic API key (only needed with PDF)", type="password", value=st.secrets.get("ANTHROPIC_API_KEY",""))
            if st.button("Build Dashboard", type="primary", disabled=(csv_file is None)):
                with st.spinner("Building dashboard..."):
                    try:
                        df = pd.read_csv(csv_file).astype(str).apply(lambda c: c.str.strip())
                        label_map = {}
                        if pdf_file and api_key:
                            try: label_map = extract_labels_from_pdf(pdf_file.read(), api_key)
                            except Exception as e: st.warning(f"PDF parsing failed ({e}) — using auto-labels")
                        questions = detect_questions(df, label_map)
                        if not questions: st.error("No question columns found."); return
                        st.session_state.df = df
                        st.session_state.questions = questions
                        st.session_state.demos = detect_demos(df)
                        st.session_state.label_map = label_map
                        st.rerun()
                    except Exception as e: st.error(f"Error: {e}")
        return

    df = st.session_state.df; questions = st.session_state.questions; demos = st.session_state.demos
    q = questions[sel_idx]; ov = compute_overall(df, q["col"])
    title = q["label"] if q["label"]!=q["col"] else f"Question {q['col']}"
    st.markdown(f'<div class="qhdr-col">{q["col"].upper()}</div><div class="qhdr-title">{title}</div><div class="qhdr-meta">n={ov["n"]:,} total respondents</div>', unsafe_allow_html=True)
    st.markdown(stat_cards_html(ov, q), unsafe_allow_html=True)
    st.markdown('<hr style="border:none;border-top:1px solid #e8e5e0;margin:1.25rem 0">', unsafe_allow_html=True)
    c1, c2 = st.columns([4,1])
    with c1:
        demo_opts = {v["label"]:k for k,v in demos.items()}
        sel_demo = demo_opts[st.selectbox("Break by", list(demo_opts.keys()), label_visibility="collapsed")]
    with c2:
        two_way = st.checkbox("2-way", value=False)
    rows, q_vals = compute_crosstab(df, q["col"], sel_demo, demos[sel_demo]["values"], two_way)
    if rows: st.markdown(crosstab_html(rows, q_vals, q, two_way), unsafe_allow_html=True)
    else: st.info("No data for this breakout.")

if __name__=="__main__": main()
