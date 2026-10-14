import html as H
import re

import pandas as pd


def boxes(h):
    out, page, last_top = [], 0, -1
    for m in re.finditer(r'<div id="a\d+" style="([^"]*)">(.*?)</div>', h, re.S):
        st, txt = m.group(1), H.unescape(re.sub("<[^>]+>", "", m.group(2))).strip()
        l = re.search(r"left:([\d.]+)px", st); t = re.search(r"top:([\d.]+)px", st)
        if not (l and t and txt): continue
        top = float(t.group(1))
        if top < last_top - 300: page += 1
        last_top = top
        out.append((page, top, float(l.group(1)), txt))
    return out
def lines(bx):
    bx = sorted(bx); res = []
    for p, top, left, txt in bx:
        if res and res[-1][0] == p and abs(res[-1][1] - top) <= 4:
            res[-1][2].append((left, txt))
        else:
            res.append([p, top, [(left, txt)]])
    return [(p, t, sorted(c)) for p, t, c in res]
def parse(h):
    i = h.lower().find("fleet employment")
    L = lines([b for b in boxes(h)])
    rows, cur, seg = [], None, None
    for p, top, cells in L:
        txt = " ".join(t for _, t in cells)
        if re.search(r"(Bulk Carriers|Capesize|Newcastlemax|Panamax|Kamsarmax|Ultramax|Post-Panamax|Methanol|Vessels? (under|to be))", txt) and len(cells) <= 2:
            seg = txt
        first = cells[0]
        if re.fullmatch(r"\d{1,2}", first[1]) and first[0] < 90 and len(cells) >= 3:
            cur = {"seq": int(first[1]), "segment": seg, "vessel": None, "rate": None, "charterer": None, "delivery": None, "redelivery": None, "built": None, "dwt": None}
            for left, t in cells[1:]:
                if 85 <= left < 235 and cur["vessel"] is None and re.search(r"[A-Za-z]{3,}", t): cur["vessel"] = t
                elif 235 <= left < 310 and cur["rate"] is None: cur["rate"] = t
                elif 360 <= left < 520: cur["charterer"] = (cur["charterer"] + " " if cur["charterer"] else "") + t
                elif 520 <= left < 620 and cur["delivery"] is None: cur["delivery"] = t
                elif 620 <= left < 750 and cur["redelivery"] is None: cur["redelivery"] = t
            rows.append(cur)
        elif cur is not None:
            m = re.search(r"\b(19\d\d|20[0-3]\d)\s+([\d,]{5,7})\b", txt)
            if m and cur["built"] is None: cur["built"], cur["dwt"] = int(m.group(1)), int(m.group(2).replace(",", ""))
            else:
                for left, t in cells:
                    if 360 <= left < 520 and cur["charterer"] and not re.search(r"\d{2}-\w{3}", t): cur["charterer"] += " " + t
                    if 620 <= left < 750 and cur["redelivery"] and re.search(r"\d", t): cur["redelivery"] += " " + t
    return pd.DataFrame(rows)
if __name__ == "__main__":
    df = parse(open("annual/DSX_fleet.htm").read())
    print(len(df)); print(df.head(12).to_string(max_colwidth=26)); print(df.tail(4).to_string(max_colwidth=26))
