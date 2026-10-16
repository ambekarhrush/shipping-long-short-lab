import re
import sys
import warnings
from io import StringIO

import pandas as pd

warnings.filterwarnings("ignore")
def clean_table(df):
    df = df.dropna(how="all").dropna(axis=1, how="all")
    df = df.astype(object).map(lambda x: "" if x is None or (isinstance(x, float) and x != x) else re.sub(r"\s+", " ", str(x)).strip())
    # collapse duplicate adjacent columns produced by colspans
    keep = []
    for c in df.columns:
        if keep and df[c].equals(df[keep[-1]]): continue
        keep.append(c)
    df = df[keep]
    df = df.loc[:, ~(df.isin(["nan", "", "$", "%", ")"]).all())]
    return df
def candidates(path):
    html = re.sub(r"<\?xml[^>]*\?>", "", open(path, "rb").read().decode("utf-8", "ignore"))
    tabs = pd.read_html(StringIO(html), flavor="lxml")
    out = []
    for k, t in enumerate(tabs):
        t = clean_table(t)
        txt = " ".join(t.head(4).astype(str).values.ravel()).lower()
        if re.search(r"dwt|deadweight|dead weight|capacity", txt) and re.search(r"built|year|delivery", txt) and len(t) >= 3:
            out.append((k, t))
    return out
if __name__ == "__main__":
    t = sys.argv[1]
    c = candidates(f"annual/{t}.htm")
    print(t, "candidate tables:", [(k, len(x)) for k, x in c])
    for k, x in c[:int(sys.argv[2]) if len(sys.argv) > 2 else 2]:
        print(f"--- table {k}"); print(x.head(6).to_string(max_colwidth=22))
