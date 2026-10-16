import re
import sys
import warnings

import pandas as pd
from extract import candidates

warnings.filterwarnings("ignore")
YEAR = re.compile(r"^(19[89]\d|20[0-3]\d)(\.0)?$")
def num(x):
    s = re.sub(r"(?i)\s*(dwt|mt|tons?)\b.*$", "", str(x)); s = re.sub(r"[,\s]", "", s); s = re.sub(r"\.0$", "", s)
    return int(s) if re.fullmatch(r"\d{4,6}", s) else None
def parse_table(t):
    t = t.reset_index(drop=True)
    cols = list(t.columns)
    # dwt column: most values look like 5,000-450,000
    best = {}
    for c in cols:
        v = t[c].map(num)
        best[c] = ((v >= 3000) & (v <= 450000)).mean() if v.notna().any() else 0
    dwt_c = max(best, key=best.get)
    if best[dwt_c] < 0.4: return None
    yr = {c: t[c].astype(str).str.fullmatch(YEAR.pattern).mean() for c in cols if c != dwt_c}
    yr_c = max(yr, key=yr.get) if yr else None
    if yr_c is None or yr[yr_c] < 0.3: yr_c = None
    # name column: text, mostly letters, high uniqueness, left of dwt
    nm = {}
    for c in cols[: cols.index(dwt_c)]:
        s = t[c].astype(str)
        ok = s.str.contains(r"[A-Za-z]{2,}") & ~s.str.contains(r"(?i)LLC|Ltd|Inc\.|Corp|S\.A\.|Shipping|Limited|Owning|Holding|Navigation Co")
        nm[c] = ok.mean() * s.nunique() / max(len(s), 1)
    if not nm: return None
    nm_c = max(nm, key=nm.get)
    rows = []
    for _, r in t.iterrows():
        d = num(r[dwt_c])
        if d is None or not (3000 <= d <= 450000): continue
        name = re.sub(r"\s*\(\d+\)|\*+|​", "", str(r[nm_c])).strip()
        if not re.search(r"[A-Za-z]", name) or len(name) > 40: continue
        built = r[yr_c] if yr_c is not None else None
        extra = " | ".join(str(r[c]) for c in cols if c not in (nm_c, dwt_c, yr_c) and str(r[c]) not in ("", "nan"))[:120]
        rows.append({"vessel": name, "dwt": d, "built": int(float(built)) if built and YEAR.match(str(built)) else None, "context": extra})
    return pd.DataFrame(rows)
def all_tables(path):
    from io import StringIO

    from extract import clean_table
    html = re.sub(r"<\?xml[^>]*\?>", "", open(path, "rb").read().decode("utf-8", "ignore"))
    return [clean_table(t) for t in pd.read_html(StringIO(html), flavor="lxml")]

SALE = re.compile(r"(?i)sold|sale price|disposal|delivered to (its|the) (new )?buyer|purchase price|loan|facility|lease")

def company(t, span=15):
    tabs = all_tables(f"annual/{t}.htm")
    cand = [k for k, x in candidates(f"annual/{t}.htm")]
    if not cand: return pd.DataFrame()
    k0 = cand[0]
    frames = []
    for k in range(k0, min(k0 + span, len(tabs))):
        head = " ".join(tabs[k].head(3).astype(str).values.ravel())
        if SALE.search(head): continue
        p = parse_table(tabs[k])
        if p is not None and len(p) >= 2: p["table"] = k; frames.append(p)
    if not frames: return pd.DataFrame()
    df = pd.concat(frames)
    df["vkey"] = df["vessel"].str.upper().str.replace(r"[^A-Z0-9 ]", "", regex=True).str.strip()
    return df.drop_duplicates("vkey")
if __name__ == "__main__":
    out = {}
    for t in sys.argv[1:]:
        try: df = company(t)
        except Exception as e: print(t, "ERROR", e); continue
        df.insert(0, "company", t); out[t] = df
        print(f"{t}: {len(df)} vessels from tables {sorted(df['table'].unique().tolist()) if len(df) else []}")
    if out: pd.concat(out.values()).to_csv("fleet_raw.csv", index=False)
