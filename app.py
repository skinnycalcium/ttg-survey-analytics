import streamlit as st
import pandas as pd
import io
import json
import re
from anthropic import Anthropic

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="TTG Survey Analytics",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ── Custom CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
[data-testid="stSidebar"] { background-color: #0D1F2D; }
[data-testid="stSidebar"] * { color: white !important; }
[data-testid="stSidebar"] .stRadio label { color: rgba(255,255,255,0.75) !important; font-size: 13px; }
[data-testid="stSidebar"] .stRadio label:hover { color: white !important; }
[data-testid="stSidebar"] hr { border-color: rgba(255,255,255,0.1); }
[data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2,
[data-testid="stSidebar"] h3 { color: white !important; }
.stMetric { background: #f8f7f5; border-radius: 8px; padding: 12px !important; }
.block-container { padding-top: 2rem; }
h1 { color: #0D1F2D !important; }
.stDataFrame { border-radius: 8px; overflow: hidden; }
div[data-testid="stMetricValue"] { font-size: 28px !important; }
</style>
""", unsafe_allow_html=True)

# ── Constants ─────────────────────────────────────────────────────────────────
COLORS = ["#C0392B","#2874A6","#7D6608","#1A7A4A","#6C3483","#D35400","#5D6D7E","#2E4057"]

DEMO_CONFIG = {
    "qgeo":         {"label": "DMA",            "values": {"1":"Tampa","2":"Orlando","3":"Miami/FLL","4":"Jacksonville","5":"Ft. Myers","6":"GNV/TLH","7":"PNS/PCB","8":"W. Palm Beach"}},
    "qparty":       {"label": "Party",           "values": {"1":"Republican","2":"Democrat","3":"Unaffiliated"}},
    "qgender":      {"label": "Gender",          "values": {"1":"Male","2":"Female"}},
    "qrace":        {"label": "Race",            "values": {"1":"White","2":"Black","3":"Hispanic","4":"Other"}},
    "qage":         {"label": "Age",             "values": {"1":"18-29","2":"30-44","3":"45-54","4":"55-64","5":"65-74","6":"75+"}},
    "qqideology":   {"label": "Ideology",        "values": {"1":"Very Liberal","2":"Somewhat Liberal","3":"Somewhat Conservative","4":"Very Conservative","5":"Moderate"}},
    "qq24presvote": {"label": "2024 Pres Vote",  "values": {"1":"Trump","2":"Harris","3":"Other","4":"Didn't Vote"}},
    "qqmaga":       {"label": "MAGA ID",         "values": {"1":"MAGA","2":"Non-MAGA"}},
    "qqmethod":     {"label": "Vote Method",     "values": {"1":"Vote by Mail","2":"Early In-Person","3":"Election Day"}},
    "qvote":        {"label": "Vote History",    "values": {"1":"New Voter","2":"1 of 3","3":"2 of 3","4":"3 of 3"}},
    "qptype":       {"label": "Interview Mode",  "values": {"3":"Landline","4":"Cell","5":"SMS"}},
    "q_lang":       {"label": "Language",        "values": {"1":"Spanish","2":"English"}},
}

META_COLS = {
    "quniqueid","groupid","api_id","phone","firstname","lastname","regis_date","age",
    "voter_id","address","city","state","zip","st_up_hous","st_lo_hous","cong_dist",
    "ai_county_","vtr_gen16","vtr_gen20","vtr_gen24","cnty_comm","dma_name",
    *[k.lower() for k in DEMO_CONFIG]
}

SKIP_VALS = {"98","99"," ",""}

# ── Helpers ───────────────────────────────────────────────────────────────────
def clean(val):
    return str(val).strip() if pd.notna(val) else ""

def infer_scale(col, unique_vals):
    cl = col.lower()
    vs = sorted([v for v in unique_vals if v not in SKIP_VALS], key=lambda x: (int(x) if x.isdigit() else 999))
    n = len(vs)
    has = lambda v: str(v) in vs
    if cl == "q01" and n == 2:
        return {"1":"Definitely Yes","2":"Probably Yes"}
    if re.match(r"^q0[23]$", cl) and n == 4:
        return {"1":"Strongly Approve","2":"Somewhat Approve","3":"Somewhat Disapprove","4":"Strongly Disapprove","98":"Unsure"}
    if has(6) and re.match(r"^q04", cl):
        return {"1":"Very Favorable","2":"Somewhat Favorable","3":"Somewhat Unfavorable","4":"Very Unfavorable","5":"No Opinion","6":"Never Heard Of"}
    if re.match(r"^q1[3]", cl) and n == 4:
        return {"1":"Much More Likely","2":"Somewhat More Likely","3":"Somewhat Less Likely","4":"Much Less Likely","98":"Unsure"}
    if n == 3 and has(1) and has(2) and has(3) and re.match(r"^q1[0-4]", cl):
        return {"1":"Republican","2":"Democrat","3":"Independent","98":"Unsure"}
    if cl == "q17" and n == 4:
        return {"1":"A lot","2":"A little","3":"Some","4":"Not at all"}
    if n == 2 and has(1) and has(2):
        return {"1":"Yes","2":"No","98":"Unsure"}
    if n == 4 and has(1) and has(4):
        return {"1":"Strongly Agree","2":"Somewhat Agree","3":"Somewhat Disagree","4":"Strongly Disagree","98":"Unsure"}
    return {}

def detect_questions(df, label_map):
    cols = df.columns.tolist()
    questions = []
    for col in cols:
        cl = col.lower()
        if not re.match(r"^q\d", cl): continue
        if cl in META_COLS: continue
        unique = set(df[col].dropna().astype(str).str.strip().unique()) - SKIP_VALS
        if len(unique) < 2: continue
        all_unique = set(df[col].dropna().astype(str).str.strip().unique())
        questions.append({
            "col": col,
            "label": label_map.get(col.lower(), label_map.get(col, col)),
            "values": infer_scale(col, all_unique)
        })
    return questions

def detect_demos(df):
    cols_lower = {c.lower(): c for c in df.columns}
    result = {}
    for k, v in DEMO_CONFIG.items():
        if k.lower() in cols_lower:
            actual_col = cols_lower[k.lower()]
            result[actual_col] = v
    return result

def get_label(q_config, val):
    v = str(val)
    return q_config["values"].get(v, q_config["values"].get(val, f"Option {val}"))

def compute_overall(df, col):
    vals = sorted(
        [v for v in df[col].dropna().astype(str).str.strip().unique() if v not in SKIP_VALS and v not in {"98","99"}],
        key=lambda x: (int(x) if x.isdigit() else 999)
    )
    n = len(df)
    counts = {v: (df[col].astype(str).str.strip() == v).sum() for v in vals}
    unsure = df[col].astype(str).str.strip().isin(["98","99"]).sum()
    pcts = {v: counts[v]/n*100 for v in vals}
    return {"n": n, "vals": vals, "counts": counts, "pcts": pcts, "unsure": unsure, "unsure_pct": unsure/n*100}

def compute_crosstab(df, q_col, by_col, demo_values, two_way=False):
    q_vals = sorted(
        [v for v in df[q_col].dropna().astype(str).str.strip().unique() if v not in SKIP_VALS and v not in {"98","99"}],
        key=lambda x: (int(x) if x.isdigit() else 999)
    )
    rows = []
    for dk, group_label in demo_values.items():
        mask = df[by_col].astype(str).str.strip() == str(dk)
        grp = df[mask]
        if len(grp) == 0: continue
        unsure = grp[q_col].astype(str).str.strip().isin(["98","99"]).sum()
        counts = {v: (grp[q_col].astype(str).str.strip() == v).sum() for v in q_vals}
        total = sum(counts.values()) + unsure
        dec_n = sum(counts.values())
        if total == 0: continue
        if two_way:
            pcts = {v: counts[v]/dec_n*100 if dec_n > 0 else 0 for v in q_vals}
        else:
            pcts = {v: counts[v]/total*100 for v in q_vals}
        rows.append({
            "Group": group_label,
            "n": total,
            **{v: pcts[v] for v in q_vals},
            "Unsure": unsure/total*100 if not two_way else None
        })
    return rows, q_vals

# ── PDF + AI label extraction ─────────────────────────────────────────────────
def extract_labels_from_pdf(pdf_bytes, api_key):
    import base64
    client = Anthropic(api_key=api_key)
    b64 = base64.standard_b64encode(pdf_bytes).decode("utf-8")
    msg = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=2000,
        messages=[{
            "role": "user",
            "content": [
                {"type": "document", "source": {"type": "base64", "media_type": "application/pdf", "data": b64}},
                {"type": "text", "text": 'This is a survey data key. Extract every variable name and its question text. Return ONLY valid JSON, no markdown, no extra text. Format: {"q01": "Full question text", "q02": "Full question text", "q04_1": "Name ID: Byron Donalds"}'}
            ]
        }]
    )
    raw = msg.content[0].text.strip().replace("```json","").replace("```","").strip()
    return json.loads(raw)

# ── Main App ──────────────────────────────────────────────────────────────────
def main():
    # Sidebar header
    with st.sidebar:
        st.markdown("## TTG Survey Analytics")
        st.markdown("*The Tyson Group · P2 Insights*")
        st.divider()

    # Session state init
    if "df" not in st.session_state:
        st.session_state.df = None
    if "questions" not in st.session_state:
        st.session_state.questions = []
    if "demos" not in st.session_state:
        st.session_state.demos = {}
    if "label_map" not in st.session_state:
        st.session_state.label_map = {}

    # ── Upload screen ─────────────────────────────────────────────────────────
    if st.session_state.df is None:
        st.title("TTG Survey Analytics")
        st.markdown("Upload your survey return file to generate instant crosstab analysis across all questions.")
        st.divider()

        col1, col2 = st.columns([1,1], gap="large")

        with col1:
            csv_file = st.file_uploader("Survey data CSV", type=["csv"], help="Your raw survey return file")
            pdf_file = st.file_uploader("Data key PDF", type=["pdf"], help="Optional — used to extract question labels automatically")

        with col2:
            api_key = st.text_input(
                "Anthropic API key",
                type="password",
                help="Required only if uploading a PDF data key. Get yours at console.anthropic.com",
                value=st.secrets.get("ANTHROPIC_API_KEY", "")
            )
            st.caption("Your API key is never stored. Add it to Streamlit secrets to avoid entering it each time.")

        if st.button("Build Dashboard", type="primary", disabled=(csv_file is None)):
            with st.spinner("Processing..."):
                try:
                    df = pd.read_csv(csv_file)
                    df = df.astype(str).apply(lambda c: c.str.strip())

                    label_map = {}

                    # Try PDF extraction if provided
                    if pdf_file and api_key:
                        try:
                            with st.spinner("Extracting question labels from PDF..."):
                                label_map = extract_labels_from_pdf(pdf_file.read(), api_key)
                                st.success(f"Extracted {len(label_map)} question labels from PDF")
                        except Exception as e:
                            st.warning(f"PDF label extraction failed ({e}) — using auto-labels")

                    questions = detect_questions(df, label_map)
                    demos = detect_demos(df)

                    if not questions:
                        st.error("No question columns detected. Make sure your CSV uses q01, q02 etc. naming.")
                    else:
                        st.session_state.df = df
                        st.session_state.questions = questions
                        st.session_state.demos = demos
                        st.session_state.label_map = label_map
                        st.rerun()

                except Exception as e:
                    st.error(f"Error loading file: {e}")
        return

    # ── Dashboard ─────────────────────────────────────────────────────────────
    df = st.session_state.df
    questions = st.session_state.questions
    demos = st.session_state.demos

    with st.sidebar:
        st.caption(f"{len(df):,} respondents · {len(questions)} questions")
        st.divider()

        q_labels = [f"{q['col']} — {q['label']}" if q['label'] != q['col'] else q['col'] for q in questions]
        selected_idx = st.radio("Select question", range(len(questions)), format_func=lambda i: q_labels[i], label_visibility="collapsed")
        st.divider()

        if st.button("← New survey"):
            for key in ["df","questions","demos","label_map"]:
                st.session_state.pop(key, None)
            st.rerun()

    # Main panel
    q = questions[selected_idx]
    ov = compute_overall(df, q["col"])

    st.markdown(f"<div style='font-size:11px;color:#888;font-family:monospace;margin-bottom:2px'>{q['col'].upper()}</div>", unsafe_allow_html=True)
    st.markdown(f"### {q['label'] if q['label'] != q['col'] else 'Question ' + q['col']}")
    st.caption(f"n={ov['n']:,} total respondents")

    # Overall cards
    cols = st.columns(min(len(ov["vals"]) + (1 if ov["unsure"] > 0 else 0), 6))
    for i, v in enumerate(ov["vals"]):
        with cols[i % len(cols)]:
            lbl = get_label(q, v)
            st.metric(label=lbl, value=f"{ov['pcts'][v]:.1f}%", help=f"n={ov['counts'][v]}")
    if ov["unsure"] > 0:
        with cols[len(ov["vals"]) % len(cols)]:
            st.metric(label="Unsure/Refused", value=f"{ov['unsure_pct']:.1f}%", help=f"n={ov['unsure']}")

    st.divider()

    # Crosstab controls
    c1, c2, c3 = st.columns([2, 2, 1])
    with c1:
        demo_options = {v["label"]: k for k, v in demos.items()}
        selected_demo_label = st.selectbox("Break by", list(demo_options.keys()))
        selected_demo_col = demo_options[selected_demo_label]
    with c2:
        pass
    with c3:
        two_way = st.checkbox("2-way", value=False, help="Exclude unsure/refused from denominator")

    # Build crosstab table
    demo_values = demos[selected_demo_col]["values"]
    ct_rows, q_vals = compute_crosstab(df, q["col"], selected_demo_col, demo_values, two_way)

    if ct_rows:
        val_labels = [get_label(q, v) for v in q_vals]
        display_cols = ["Group", "n"] + val_labels + (["Unsure%"] if not two_way else [])

        table_data = []
        for row in ct_rows:
            r = {"Group": row["Group"], "n": row["n"]}
            for v, lbl in zip(q_vals, val_labels):
                r[lbl] = f"{row[v]:.1f}%"
            if not two_way:
                r["Unsure%"] = f"{row['Unsure']:.1f}%" if row["Unsure"] is not None else "—"
            table_data.append(r)

        result_df = pd.DataFrame(table_data)

        # Style the table
        def style_pct(val):
            if not isinstance(val, str) or not val.endswith("%"): return ""
            try:
                n = float(val.replace("%",""))
                if n >= 60: return "font-weight: bold; color: #0D1F2D"
                if n >= 50: return "color: #0D1F2D"
            except: pass
            return ""

        try:
            styled = result_df.style.map(style_pct, subset=val_labels)
        except AttributeError:
            styled = result_df.style.applymap(style_pct, subset=val_labels)
        st.dataframe(styled, use_container_width=True, hide_index=True)
        suffix = " (2-way — decided only)" if two_way else " (incl. unsure in denominator)"
        st.caption(f"Percentages{suffix}. {len(df):,} total respondents.")
    else:
        st.warning("No crosstab data for this combination.")

if __name__ == "__main__":
    main()
