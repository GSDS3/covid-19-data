# -*- coding: utf-8 -*-
"""
골격(skeleton/*.json)에 5개 보고서의 실제 근거(inputs/derived, inputs/aggregate_a0002)를 결합해
dist/skeleton.json 을 만든다. 이어서 render_html.py 가 dist/index.html 을 생성한다.

결합 규칙
- 보고서 목차(L1/L2/L3)를 템플릿 노드에 대응한다. L1은 로마숫자, L2는 순번+명칭(별칭 포함),
  III.2/III.4의 L3는 재무제표 명칭, III.3/III.5의 L3는 주석 제목 키워드 -> 주석 주제 유형.
- 각 발견(findings)은 귀속된 가장 깊은 절의 템플릿 노드에 매단다.
- a0002 유형·규칙 후보는 supporting_discoveries 의 발견 ID를 따라 노드에 매단다.
- 노드별로 보고서 존재 여부, 표·셀·문단 수, 관찰된 소제목을 인스턴스 오버레이로 붙인다.
"""
import json, os, re, collections, datetime

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SK = os.path.join(ROOT, "skeleton")
IN = os.path.join(ROOT, "inputs")
DIST = os.path.join(ROOT, "dist")
os.makedirs(DIST, exist_ok=True)

def load(p):
    with open(p, encoding="utf-8") as f:
        return json.load(f)

def load_jsonl(p):
    rows = []
    with open(p, encoding="utf-8") as f:
        for l in f:
            if l.strip():
                rows.append(json.loads(l))
    return rows

template = load(os.path.join(SK, "data_tree_template.json"))
info = load(os.path.join(SK, "info_tree.json"))
mapping = load(os.path.join(SK, "mapping.json"))
obs = load(os.path.join(SK, "observation_schema.json"))
docmap = load(os.path.join(SK, "dart_document_map.json"))
sections = load(os.path.join(IN, "derived", "sections_findings.json"))
status = load(os.path.join(IN, "derived", "report_status.json"))
types_a = load_jsonl(os.path.join(IN, "aggregate_a0002", "type_catalog.jsonl"))
types_a0001 = {t["id"].split("/")[-1]: t for t in load_jsonl(os.path.join(IN, "aggregate_a0001", "type_catalog.jsonl"))} if os.path.exists(os.path.join(IN, "aggregate_a0001", "type_catalog.jsonl")) else {}
rules_a = load_jsonl(os.path.join(IN, "aggregate_a0002", "rule_candidates.jsonl"))
maps_a = load_jsonl(os.path.join(IN, "aggregate_a0002", "local_global_map.jsonl"))

REPORT_ORDER = ["BR0001", "BR0044", "BR0053", "BR0016", "BR0020"]

# ---------------------------------------------------------------- index nodes
nodes = {}
def index(n, parent=None):
    n["parent"] = parent
    nodes[n["id"]] = n
    for c in n["children"]:
        index(c, n["id"])
index(template["root"])

def child_by_code(nid, code):
    for c in nodes[nid]["children"]:
        if c["code"] == code:
            return c
    return None

ROMAN = {"I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X", "XI", "XII"}

def norm(t):
    return re.sub(r"[\s·ㆍ()（）\[\]【】]", "", t)

# 주석 제목 -> 주제 유형 (구체적인 키워드부터)
NOTE_KW = [
    ("온실가스", "N31"), ("보험", "N30"), ("재보험", "N30"), ("사업결합", "N28"), ("합병", "N28"),
    ("보고기간후", "N29"), ("보고기간 후", "N29"), ("후속사건", "N29"),
    ("특수관계", "N27"), ("부문", "N26"), ("영업으로부터창출된현금", "N25"), ("현금흐름", "N25"),
    ("주당", "N24"), ("기타수익", "N23"), ("기타비용", "N23"), ("기타손익", "N23"), ("금융수익", "N23"), ("금융비용", "N23"), ("금융손익", "N23"), ("파생", "N23"),
    ("성격별", "N22"), ("판매비", "N22"), ("판관비", "N22"),
    ("매출액", "N21"), ("매출원가", "N21"), ("수익", "N21"),
    ("법인세", "N19"), ("정부보조금", "N18"),
    ("종업원급여", "N17"), ("퇴직급여", "N17"), ("확정급여", "N17"), ("주식기준보상", "N17"),
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

def note_topic(title):
    t = norm(re.sub(r"^\d{1,2}[.\s]*", "", title)).replace("연결", "")
    for kw, code in NOTE_KW:
        if norm(kw) in t:
            return code
    return None

STATEMENT_KW = [("포괄손익계산서", "03"), ("손익계산서", "02"), ("재무상태표", "01"), ("자본변동표", "04"), ("현금흐름표", "05"), ("이익잉여금처분", "06"), ("결손금처리", "06")]

def match_l1(text):
    t = text.strip()
    if "사 업 보 고 서" in t or t.replace(" ", "") == "사업보고서":
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
    l1 = nodes[l1id]
    # alias match first (업종 변형)
    for c in l1["children"]:
        if any(norm(a) == norm(t) for a in c.get("aliases", [])):
            return c["id"]
    for c in l1["children"]:
        if norm(c["title"]) == norm(title):
            return c["id"]
    c = child_by_code(l1id, ordn)
    if c and c["level"] == 2:
        return c["id"]
    # fallback: title containment
    for c in l1["children"]:
        if norm(title)[:6] and norm(title)[:6] in norm(c["title"]):
            return c["id"]
    return None

def match_l3(l2id, text):
    l2 = nodes[l2id]
    code2 = l2["code"]
    l1code = nodes[l2["parent"]]["code"]
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

# ---------------------------------------------------------------- per-report overlay
for n in nodes.values():
    n["instances"] = {}
    n["findings"] = []
    n["rules"] = []

section_node = {}  # (br, section_idx) -> node id
for br in REPORT_ORDER:
    r = sections[br]
    secs = r["sections"]
    cur1 = cur2 = None
    for i, x in enumerate(secs):
        nid = None
        if x["level"] == 1:
            nid = match_l1(x["text"]); cur1 = nid; cur2 = None
        elif x["level"] == 2 and cur1:
            nid = match_l2(cur1, x["text"]); cur2 = nid
        elif x["level"] == 3 and cur2:
            nid = match_l3(cur2, x["text"])
        section_node[(br, i)] = nid
        if nid and x.get("pos") is not None:
            inst = nodes[nid]["instances"].setdefault(br, {"present": True, "sections": [], "counts": {"table": 0, "cell": 0, "paragraph": 0, "image": 0}, "subheads": []})
            inst["sections"].append(x["text"])
            c = x.get("counts") or {}
            for k in inst["counts"]:
                inst["counts"][k] += c.get(k, 0) or 0
            inst["subheads"].extend(x.get("subheads") or [])
        elif nid:
            nodes[nid]["instances"].setdefault(br, {"present": False, "sections": [x["text"]], "counts": None, "subheads": []})

# 존재 여부 판정: 노드 범위 안에 표/셀/문단이 하나도 없으면 '빈 절'(서식상 제목만 존재)
for n in nodes.values():
    for br, inst in n["instances"].items():
        if inst["present"] and inst["counts"] and sum(inst["counts"].values()) == 0:
            inst["present"] = "empty"

# 목차에 대응 절이 없는 템플릿 노드(예: IV·VII·IX·X 의 항목, 각 절의 표 유형 L3)는
# 상위 절이 존재하면 '상위 절에 포함(개별 존재 미판정)'으로 표시한다.
# 단, 같은 보고서에서 형제 노드 중 하나라도 목차에서 직접 대응된 것이 있으면(예: 보험업 II장의 F1~F4)
# 나머지 형제는 '없음'으로 둔다(그 보고서의 절 구성이 다르다는 사실).
for br in REPORT_ORDER:
    template["root"]["instances"][br] = {"present": True, "sections": ["(문서 전체)"], "counts": None, "subheads": []}
def inherit_presence(n):
    for br in REPORT_ORDER:
        if n["instances"].get(br, {}).get("present") is not True:
            continue
        sibling_matched = any(c["instances"].get(br, {}).get("present") in (True, "empty") for c in n["children"])
        if sibling_matched:
            continue
        for c in n["children"]:
            if br not in c["instances"]:
                c["instances"][br] = {"present": "within_parent", "sections": [], "counts": None, "subheads": []}
    for c in n["children"]:
        inherit_presence(c)
inherit_presence(template["root"])

# 자식 없는 L3 템플릿 노드의 '소제목 관찰' 휴리스틱
def key_terms(title):
    parts = re.split(r"[·/()（）,\s]", title)
    return [p for p in parts if len(p) >= 3][:4]

for n in nodes.values():
    if n["level"] == 3 and not n["children"]:
        parent = nodes[n["parent"]]
        seen = {}
        terms = key_terms(n["title"])
        for br, inst in parent["instances"].items():
            hits = [h for h in inst.get("subheads", []) if any(t in h for t in terms)]
            if hits:
                seen[br] = hits[:4]
        n["subhead_evidence"] = seen

# ---------------------------------------------------------------- findings
findings_index = {}
for br in REPORT_ORDER:
    r = sections[br]
    for f in r["findings"]:
        fid = f"{br}/{f['id']}"
        nid = None
        if f.get("section_idx") is not None:
            nid = section_node.get((br, f["section_idx"]))
            # deepest matched ancestor: section_idx may be L3 unmatched -> walk up path
            if nid is None:
                path = f.get("section_path") or []
                secs = r["sections"]
                # find indices of ancestors by text
                for depth in range(len(path) - 1, -1, -1):
                    for i, x in enumerate(secs):
                        if x["text"] == path[depth] and x["level"] == depth + 1 and section_node.get((br, i)):
                            nid = section_node[(br, i)]; break
                    if nid:
                        break
        rec = {"id": fid, "report": br, "company": r["company"], "local_id": f["id"], "record_type": f.get("record_type"),
               "summary": f.get("summary"), "evidence": f.get("evidence") or [], "section_path": f.get("section_path") or [],
               "node": nid, "proposal": f.get("proposal")}
        findings_index[fid] = rec
        if nid:
            nodes[nid]["findings"].append(fid)

# ---------------------------------------------------------------- rules (a0002)
rules = []
type_by_id = {t["id"]: t for t in types_a}
for rl in rules_a:
    tid = rl.get("type_id")
    t = type_by_id.get(tid, {})
    inherited = rl.get("inherited_from")
    if inherited and not t:
        # a0001 승계 규칙: a0001 유형 카탈로그의 정의·지원 발견을 사용
        t = types_a0001.get(inherited.split("/")[-1].replace("R", "T"), {})
        tid = t.get("id", tid)
    rec = {"id": rl["id"], "type_id": tid, "label": t.get("label"), "definition": t.get("definition_draft"),
           "state": rl.get("state"), "application": rl.get("application") or t.get("definition_draft"), "rejection": rl.get("rejection") or t.get("counterexample_guard"),
           "failure_handling": rl.get("failure_handling"), "required_context": rl.get("required_context") or t.get("required_context") or [],
           "counterexample_guard": t.get("counterexample_guard"), "supporting": rl.get("supporting_discoveries") or t.get("local_discoveries") or [],
           "inherited_from": inherited, "nodes": []}
    for d in rec["supporting"]:
        m = re.match(r"(BR\d{4})/r\d+/finding/(.+)", d)
        if m:
            fid = f"{m.group(1)}/{m.group(2)}"
            fr = findings_index.get(fid)
            if fr and fr["node"]:
                rec["nodes"].append(fr["node"])
                nodes[fr["node"]]["rules"].append(rl["id"])
    rec["nodes"] = sorted(set(rec["nodes"]))
    rules.append(rec)
# a0001 승계 7개 유형(내용은 a0001 카탈로그에 있으며 여기서는 라벨만 보존)
A0001_LABELS = {"T0001": "같은 표 안의 대상·연결범위 예외", "T0002": "계획·잠정·기말·지급 사건의 시간 역할", "T0003": "분모·산식이 다른 비율", "T0004": "투자·지배·기초자산의 다단 관계", "T0005": "반복 발생과 기재 충돌", "T0006": "열별 기준 전환과 미적용 정책", "T0007": "대시·공란·명시0·해당없음의 의미 분리"}
for rec in rules:
    if rec["inherited_from"] and not rec["label"]:
        code = rec["inherited_from"].split("/")[-1]
        rec["label"] = A0001_LABELS.get(code.replace("R", "T"), code)
        rec["type_id"] = "a0001/type/" + code.replace("R", "T")
        rec["definition"] = "a0001 후보를 재검증 없이 이력으로 승계(prior_candidate_preserved_not_revalidated)."
for n in nodes.values():
    n["rules"] = sorted(set(n["rules"]))

# ---------------------------------------------------------------- mapping onto nodes
info_nodes = {}
def index_it(n, parent=None):
    n["parent"] = parent; info_nodes[n["id"]] = n
    n["data_topic"] = []; n["data_item"] = []
    for c in n["children"]:
        index_it(c, n["id"])
index_it(info["root"])
for n in nodes.values():
    n["mapping"] = {"topic": [], "item": []}
missing = []
for e in mapping["edges"]:
    d = e["data"]
    if d not in nodes:
        missing.append(d); continue
    for i in e["info"]:
        if i not in info_nodes:
            missing.append(i); continue
        nodes[d]["mapping"][e["level"]].append(i)
        (info_nodes[i]["data_topic"] if e["level"] == "topic" else info_nodes[i]["data_item"]).append(d)
if missing:
    print("WARNING unmatched mapping ids:", sorted(set(missing)))

# ---------------------------------------------------------------- roll-ups
def rollup(n):
    tot = collections.Counter()
    for f in n["findings"]:
        tot[findings_index[f]["report"]] += 1
    for c in n["children"]:
        sub = rollup(c)
        tot.update(sub)
    n["stats"] = {"findings_total": sum(tot.values()), "findings_by_report": dict(tot),
                  "findings_here": len(n["findings"]), "rules_here": len(n["rules"]),
                  "reports_present": [br for br in REPORT_ORDER if n["instances"].get(br, {}).get("present") is True],
                  "reports_empty": [br for br in REPORT_ORDER if n["instances"].get(br, {}).get("present") == "empty"]}
    return tot
rollup(template["root"])

# info tree finding counts via mapped data nodes (item > topic)
def it_stats(n):
    items = set(n["data_item"]); topics = set(n["data_topic"])
    for c in n["children"]:
        ci, ct = it_stats(c)
        items |= ci; topics |= ct
    n["stats"] = {"findings_via_items": sum(nodes[d]["stats"]["findings_here"] for d in items),
                  "findings_via_all": sum(nodes[d]["stats"]["findings_here"] for d in (items | topics)),
                  "data_nodes_item": len(items), "data_nodes_topic": len(topics),
                  "rolled_up": bool(n["children"])}
    return items, topics
it_stats(info["root"])

# observed context type counts -> canonical
canon = {}
for c in obs["context_relation_types"]:
    for s in c["observed_synonyms"]:
        canon[s] = c["canonical"]
ctx_counts = collections.defaultdict(lambda: collections.Counter())
uncanon = collections.Counter()
for br, cc in status["context_type_counts"].items():
    for k, v in cc.items():
        can = canon.get(k)
        if can:
            ctx_counts[can][br] += v
        else:
            uncanon[k] += v
for c in obs["context_relation_types"]:
    c["observed_count"] = dict(ctx_counts.get(c["canonical"], {}))
    c["observed_total"] = sum(ctx_counts.get(c["canonical"], {}).values())
obs["uncanonical_observed"] = dict(uncanon)

# ---------------------------------------------------------------- write
def strip_parent(n):
    n.pop("parent", None)
    for c in n["children"]:
        strip_parent(c)
strip_parent(template["root"]); strip_parent(info["root"])

out = {
    "meta": {"generated_utc": datetime.datetime.utcnow().replace(microsecond=0).isoformat() + "Z",
             "title": "사업보고서 공통 데이터체계 골격 v0.1",
             "reports": [dict(status["reports"][br], id=br) for br in REPORT_ORDER],
             "batch": status["batch"],
             "counts": {"data_nodes": len(nodes), "info_nodes": len(info_nodes), "mapping_edges": len(mapping["edges"]), "findings": len(findings_index), "rules": len(rules)}},
    "document_map": docmap,
    "data_tree": template["root"],
    "structure_layers": template["structure_layers"],
    "note_topics": template["note_topics"],
    "info_tree": info["root"],
    "skills": info["skills"],
    "mapping": {"levels": mapping["levels"], "rules": mapping["rules"], "edge_count": len(mapping["edges"])},
    "observation_schema": obs,
    "rules": rules,
    "findings": findings_index,
}
p = os.path.join(DIST, "skeleton.json")
with open(p, "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False, indent=1)
print("data nodes", len(nodes), "| info nodes", len(info_nodes), "| findings", len(findings_index), "| located", sum(1 for f in findings_index.values() if f["node"]), "| rules", len(rules))
print("written", p, os.path.getsize(p), "bytes")
# diagnostics: unmatched sections
unm = collections.Counter()
for (br, i), nid in section_node.items():
    if nid is None:
        x = sections[br]["sections"][i]
        unm[(x["level"], x["text"][:40])] += 1
print("unmatched sections:", sum(unm.values()))
for k, v in list(unm.items())[:40]:
    print("   ", k, v)
