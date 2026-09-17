# -*- coding: utf-8 -*-
"""
보고서 1건의 '구조 조사'(structural survey).  셀 단위 의미 판별을 하지 않고, 골격 검증에 필요한 만큼만 본다.

입력:  DART 뷰어 wrapper.html (또는 acquisition.json 의 wrapper_toc) + 본문 HTML (이미지 내장본 또는 원 응답)
출력:  inputs/reports/BRxxxx/structure.json
  - identity        회사·사업연도·접수번호
  - toc             wrapper 목차(레벨·제목)와 본문 앵커 위치(줄바꿈 포함 코드포인트 기준)
  - sections        각 목차 항목의 템플릿 노드 대응(id), 범위, 표·셀·문단·그림 수, 소제목
  - tables          표 카탈로그: 소속 절, 직전 캡션(제목), 단위 표기, 머리글 행, 행·열 수, 병합 여부
  - unmatched       템플릿에 대응되지 않은 목차 항목(골격 개정 후보)

사용:  python3 build/survey_structure.py BR0043 --html path/to/body.html --wrapper path/to/wrapper.html \
           --company 신영증권 --year 2023 --receipt 2023xxxxxxxxxx [--sector 금융(증권)]
"""
import re, json, os, sys, html as htmlmod, argparse, collections, hashlib

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SK = os.path.join(ROOT, "skeleton")

def norm(t):
    return re.sub(r"[\s·ㆍ()（）\[\]【】]", "", t or "")

def strip_tags(h):
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", htmlmod.unescape(h)).replace("\xa0", " ")).strip()

# ----------------------------------------------------------------- template
template = json.load(open(os.path.join(SK, "data_tree_template.json"), encoding="utf-8"))
NODES = {}
def _index(n, parent=None):
    n["_parent"] = parent; NODES[n["id"]] = n
    for c in n["children"]:
        _index(c, n["id"])
_index(template["root"])

def child_by_code(nid, code):
    for c in NODES[nid]["children"]:
        if c["code"] == code:
            return c
    return None

ROMAN = {"I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X", "XI", "XII"}
NOTE_KW = [
    ("온실가스", "N31"), ("보험", "N30"), ("재보험", "N30"), ("사업결합", "N28"), ("합병", "N28"),
    ("보고기간후", "N29"), ("후속사건", "N29"), ("특수관계", "N27"), ("부문", "N26"),
    ("영업으로부터창출된현금", "N25"), ("현금흐름", "N25"), ("주당", "N24"),
    ("기타수익", "N23"), ("기타비용", "N23"), ("기타손익", "N23"), ("금융수익", "N23"), ("금융비용", "N23"), ("금융손익", "N23"), ("파생", "N23"),
    ("성격별", "N22"), ("판매비", "N22"), ("판관비", "N22"), ("매출액", "N21"), ("매출원가", "N21"), ("수익", "N21"),
    ("법인세", "N19"), ("정부보조금", "N18"), ("종업원급여", "N17"), ("퇴직급여", "N17"), ("확정급여", "N17"), ("주식기준보상", "N17"),
    ("우발", "N16"), ("약정", "N16"), ("충당부채", "N16"), ("배출부채", "N16"),
    ("차입금", "N15"), ("사채", "N15"), ("금융부채", "N15"), ("리스", "N15"),
    ("매입채무", "N14"), ("지급채무", "N14"), ("계약부채", "N14"), ("기타부채", "N14"), ("미지급", "N14"),
    ("매각예정", "N13"), ("중단영업", "N13"), ("처분자산집단", "N13"), ("기타자산", "N13"),
    ("투자부동산", "N12"), ("무형자산", "N11"), ("영업권", "N11"), ("유형자산", "N10"), ("사용권", "N10"),
    ("관계기업", "N09"), ("공동기업", "N09"), ("종속기업", "N09"), ("지분법", "N09"),
    ("재고", "N08"), ("매출채권", "N07"), ("기타채권", "N07"), ("미수금", "N07"),
    ("현금및현금성", "N06"), ("공정가치금융자산", "N06"), ("금융자산의양도", "N06"), ("금융자산", "N06"), ("단기금융", "N06"),
    ("범주별", "N05"), ("공정가치", "N05"), ("금융상품", "N05"),
    ("재무위험", "N04"), ("위험관리", "N04"), ("자본관리", "N04"), ("자본위험", "N04"),
    ("추정", "N03"), ("가정", "N03"), ("회계정책", "N02"), ("회계처리방침", "N02"), ("기준서", "N02"),
    ("납입자본", "N20"), ("자본금", "N20"), ("이익잉여금", "N20"), ("기타자본", "N20"), ("기타포괄손익누계액", "N20"), ("비지배지분", "N20"), ("자본", "N20"),
    ("일반", "N01"), ("연결대상", "N01"),
]
STATEMENT_KW = [("포괄손익계산서", "03"), ("손익계산서", "02"), ("재무상태표", "01"), ("자본변동표", "04"), ("현금흐름표", "05"), ("이익잉여금처분", "06"), ("결손금처리", "06")]

def note_topic(title):
    t = norm(re.sub(r"^\d{1,2}[.\s]*", "", title)).replace("연결", "")
    for kw, code in NOTE_KW:
        if norm(kw) in t:
            return code
    return None

def match_l1(text):
    t = text.strip()
    if t.replace(" ", "") == "사업보고서":
        return "DT.A001.COVER"
    if "대표이사" in t:
        return "DT.A001.CONF"
    if "전문가" in t:
        return "DT.A001.EXP"
    m = re.match(r"([IVX]+)\.", t)
    if m and m.group(1) in ROMAN:
        return "DT.A001." + m.group(1)
    return None

def match_l2(l1id, text):
    t = text.strip()
    m = re.match(r"(\d+)\.\s*(.*)", t)
    if not m:
        return None
    ordn, title = m.group(1), m.group(2)
    l1 = NODES[l1id]
    for c in l1["children"]:
        if any(norm(a) == norm(t) for a in c.get("aliases", [])):
            return c["id"]
        for g in c["children"]:   # 업종별 상세표처럼 L3에 별칭이 있는 경우 -> L3로 직접 대응
            if any(norm(a) == norm(t) for a in g.get("aliases", [])):
                return g["id"]
    for c in l1["children"]:
        if norm(c["title"]) == norm(title):
            return c["id"]
    c = child_by_code(l1id, ordn)
    if c and c["level"] == 2 and norm(title)[:4] == norm(c["title"])[:4]:
        return c["id"]
    for c in l1["children"]:
        if norm(title)[:6] and norm(title)[:6] in norm(c["title"]):
            return c["id"]
    return None

def match_l3(l2id, text):
    l2 = NODES[l2id]; code2 = l2["code"]; l1code = NODES[l2["_parent"]]["code"]
    if l1code == "III" and code2 in ("2", "4"):
        for kw, code in STATEMENT_KW:
            if kw in text.replace(" ", ""):
                c = child_by_code(l2id, code)
                return c["id"] if c else None
    if l1code == "III" and code2 in ("3", "5"):
        code = note_topic(text)
        if code:
            c = child_by_code(l2id, code)
            return c["id"] if c else None
    return None

# ----------------------------------------------------------------- parsing
def parse_wrapper(w):
    toc = []
    for m in re.finditer(r"var (node(\d))\s*=\s*\{\};(.*?)(?=var node\d\s*=\s*\{\};|function |$)", w, flags=re.S):
        lvl = int(m.group(2)); body = m.group(3)
        g = lambda k: re.search(r"\['%s'\]\s*=\s*\"([^\"]*)\"" % k, body)
        t = g("text")
        if not t:
            continue
        toc.append({"level": lvl, "text": htmlmod.unescape(t.group(1)).strip(), "id": (g("id") or [None])[1] if g("id") else None,
                    "eleId": g("eleId").group(1) if g("eleId") else None, "offset": int(g("offset").group(1)) if g("offset") else None, "length": int(g("length").group(1)) if g("length") else None})
    return toc

HEAD_PAT = re.compile(r"^(?:\(?\d{1,2}\)|\d{1,2}\)|[가-힣]\.|\d{1,2}-\d{1,2}\.|\[[^\]]{2,60}\]|[①-⑳]|\(\d{1,2}-\d{1,2}\))")

def survey(sample_id, html_path, wrapper_path=None, toc_json=None, company=None, year=None, receipt=None, sector=None, period=None):
    raw = open(html_path, "rb").read()
    s = raw.decode("utf-8", errors="replace")   # 줄바꿈 포함 코드포인트 기준(nodes.jsonl 과 동일)
    sha = hashlib.sha256(raw).hexdigest()
    if toc_json:
        toc = [{"level": 1 if re.match(r"^([IVX]+\.|사\s*업|【)", t["text"]) else (3 if re.match(r"^\d+-\d+\.|^\d{1,2}\.\s*[^.]*\(연결\)", t["text"]) else 2), **t} for t in toc_json]
    else:
        toc = parse_wrapper(open(wrapper_path, encoding="utf-8", errors="replace", newline="").read())
    anchors = [(m.start(), strip_tags(m.group(2))) for m in re.finditer(r"<A name='toc(\d+)'>(.*?)</A>", s, flags=re.S | re.I)]
    xbrl = [(m.start(), strip_tags(m.group(1))) for m in re.finditer(r"<P class='table-group-xbrl'>(.*?)</P>", s, flags=re.S)]
    secs = []; ai = 0
    for t in toc:
        pos = None
        for j in range(ai, min(ai + 6, len(anchors))):
            if norm(anchors[j][1]) == norm(t["text"]):
                pos = anchors[j][0]; ai = j + 1; break
        secs.append({"level": t["level"], "text": t["text"], "pos": pos, "src": "anchor" if pos is not None else None})
    for i, sec in enumerate(secs):
        if sec["pos"] is not None:
            continue
        par = next((j for j in range(i - 1, -1, -1) if secs[j]["level"] < sec["level"]), None)
        if par is None or secs[par]["pos"] is None:
            continue
        pstart = secs[par]["pos"]; pend = len(s)
        for j in range(par + 1, len(secs)):
            if secs[j]["level"] <= secs[par]["level"] and secs[j]["pos"] is not None:
                pend = secs[j]["pos"]; break
        cands = [(p, tx) for p, tx in xbrl if pstart <= p < pend and norm(tx) == norm(sec["text"])]
        if cands:
            sec["pos"] = cands[0][0]; sec["src"] = "xbrl_heading"
    withpos = [(i, x) for i, x in enumerate(secs) if x["pos"] is not None]
    for k, (i, x) in enumerate(withpos):
        end = len(s)
        for i2, x2 in withpos[k + 1:]:
            if x2["level"] <= x["level"]:
                end = x2["pos"]; break
        x["end"] = end
    # template alignment
    cur1 = cur2 = None; unmatched = []
    for x in secs:
        nid = None
        if x["level"] == 1:
            nid = match_l1(x["text"]); cur1 = nid; cur2 = None
        elif x["level"] == 2 and cur1:
            nid = match_l2(cur1, x["text"]); cur2 = nid
        elif x["level"] == 3 and cur2:
            nid = match_l3(cur2, x["text"])
        x["node"] = nid
        if nid is None:
            unmatched.append({"level": x["level"], "text": x["text"], "parent_node": cur2 if x["level"] == 3 else (cur1 if x["level"] == 2 else None)})
    # structure counts and sub-headings straight from HTML
    tables_all = [(m.start(), m.end()) for m in re.finditer(r"<TABLE\b.*?</TABLE>", s, flags=re.S | re.I)]
    tstarts = [a for a, b in tables_all]
    import bisect
    def paragraphs(seg):
        return [strip_tags(m.group(1)) for m in re.finditer(r"<P[^>]*>(.*?)</P>", seg, flags=re.S | re.I)]
    for x in secs:
        if x["pos"] is None:
            x["counts"] = None; x["subheads"] = []; continue
        seg = s[x["pos"]:x["end"]]
        lo = bisect.bisect_left(tstarts, x["pos"]); hi = bisect.bisect_left(tstarts, x["end"])
        cells = sum(len(re.findall(r"<T[DH]\b", s[a:b], flags=re.I)) for a, b in tables_all[lo:hi])
        paras = paragraphs(seg)
        x["counts"] = {"table": hi - lo, "cell": cells, "paragraph": sum(1 for p in paras if p), "image": len(re.findall(r"<IMG\b", seg, flags=re.I))}
        x["subheads"] = [p for p in paras if 2 < len(p) < 70 and HEAD_PAT.match(p) and not p.startswith("(단위") and not p.startswith("(기준일")]
    # table catalog (deepest section containing the table)
    def deepest(pos):
        best = None
        for x in secs:
            if x["pos"] is not None and x["pos"] <= pos < x["end"]:
                if best is None or x["level"] >= best["level"]:
                    best = x
        return best
    catalog = []
    # 표 사이 '틈'의 문단(표 안의 <P>는 제외)에서 캡션·단위·기준일을 찾는다.
    # DART 는 '(단위 : ...)'/'(기준일 : ...)'/'[표제]' 를 데이터 표 직전의 작은 nb 표에 넣는 경우가 많다.
    parsed = []
    for a, b in tables_all:
        tb = s[a:b]
        kind = "layout" if ("class='nb'" in tb[:80] or 'class="nb"' in tb[:80]) else "data"
        rows = re.findall(r"<TR\b.*?</TR>", tb, flags=re.S | re.I)
        head_rows = []
        for r in rows[:3]:
            cells_ = [strip_tags(c) for c in re.findall(r"<T[DH]\b[^>]*>(.*?)</T[DH]>", r, flags=re.S | re.I)]
            if cells_:
                head_rows.append(cells_)
        ncols = max((len(re.findall(r"<T[DH]\b", r, flags=re.I)) for r in rows), default=0)
        merged = bool(re.search(r"(rowspan|colspan)=['\"]?[2-9]", tb, flags=re.I))
        flat = " ".join(" ".join(h) for h in head_rows).strip()
        parsed.append({"a": a, "b": b, "kind": kind, "rows": len(rows), "ncols": ncols, "merged": merged, "head_rows": head_rows, "flat": flat})
    prev_end = 0
    pending_meta = {"unit": None, "basedate": None, "caption": None}
    for i, t in enumerate(parsed):
        gap = s[prev_end:t["a"]]
        gap_ps = [strip_tags(m.group(1)) for m in re.finditer(r"<P[^>]*>(.*?)</P>", gap, flags=re.S | re.I)]
        gap_ps = [p for p in gap_ps if p]
        for p in gap_ps:
            if p.startswith("(단위"):
                pending_meta["unit"] = p
            elif p.startswith("(기준일"):
                pending_meta["basedate"] = p
            elif len(p) < 90:
                pending_meta["caption"] = p
        prev_end = t["b"]
        # 메타용 작은 nb 표: 단위/기준일/[표제]만 담고 있으면 다음 데이터 표의 메타로 넘긴다
        if t["kind"] == "layout" and t["rows"] <= 2 and t["ncols"] <= 4:
            f = t["flat"]
            if not f:
                continue
            if "(단위" in f:
                pending_meta["unit"] = re.search(r"\(단위[^)]*\)", f).group(0) if re.search(r"\(단위[^)]*\)", f) else f
            if "(기준일" in f or "현재]" in f or "현재)" in f:
                m = re.search(r"\(기준일[^)]*\)|\[[^\]]*현재\]|\([^)]*현재\)", f)
                pending_meta["basedate"] = m.group(0) if m else f
            if f.startswith("[") or f.startswith("【"):
                pending_meta["caption"] = f
            if "(단위" in f or "(기준일" in f or f.startswith("[") or "현재" in f:
                continue
        if t["kind"] == "layout" and t["ncols"] <= 3 and t["rows"] <= 12 and not pending_meta["caption"]:
            continue
        if t["kind"] == "layout" and t["rows"] == 1 and t["ncols"] == 1:
            # 각주(※ ...) 한 칸짜리 nb 표는 직전 데이터 표의 각주로 취급
            if catalog and t["flat"].startswith("※"):
                catalog[-1].setdefault("footnotes", []).append(t["flat"][:300])
            continue
        sec = deepest(t["a"])
        catalog.append({"pos": t["a"], "section": sec["text"] if sec else None, "node": sec["node"] if sec else None, "kind": t["kind"],
                        "caption": pending_meta["caption"], "unit": pending_meta["unit"], "basedate": pending_meta["basedate"],
                        "n_rows": t["rows"], "n_cols": t["ncols"], "merged": t["merged"], "header_rows": t["head_rows"][:2]})
        pending_meta = {"unit": None, "basedate": None, "caption": None}
    out = {"identity": {"sample_id": sample_id, "company": company, "fiscal_year": year, "receipt_id": receipt, "sector": sector, "period": period,
                        "html_sha256": sha, "html_chars": len(s), "html_bytes": len(raw)},
           "survey": {"kind": "structural_survey", "depth": "toc_alignment+section_counts+subheads+table_catalog; no cell-level semantic review"},
           "toc": [{k: t.get(k) for k in ("level", "text", "id", "offset", "length")} for t in toc],
           "sections": [{k: x.get(k) for k in ("level", "text", "pos", "end", "src", "node", "counts", "subheads")} for x in secs],
           "unmatched": unmatched,
           "tables": catalog,
           "stats": {"sections": len(secs), "aligned": sum(1 for x in secs if x["node"]), "with_pos": sum(1 for x in secs if x["pos"] is not None),
                     "tables_total": len(tables_all), "tables_cataloged": len(catalog), "unmatched": len(unmatched)}}
    return out

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("sample_id"); ap.add_argument("--html", required=True); ap.add_argument("--wrapper"); ap.add_argument("--acquisition")
    ap.add_argument("--company"); ap.add_argument("--year", type=int); ap.add_argument("--receipt"); ap.add_argument("--sector"); ap.add_argument("--period")
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    toc_json = None
    if not a.wrapper and a.acquisition:
        toc_json = json.load(open(a.acquisition, encoding="utf-8")).get("wrapper_toc")
    res = survey(a.sample_id, a.html, a.wrapper, toc_json, a.company, a.year, a.receipt, a.sector, a.period)
    out = a.out or os.path.join(ROOT, "inputs", "reports", a.sample_id, "structure.json")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    json.dump(res, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps(res["stats"], ensure_ascii=False), "->", out)
    for u in res["unmatched"][:20]:
        print("  unmatched:", u)
