# 사업보고서 공통 데이터체계 골격 (br-data-structure)

DART 사업보고서(A001)를 대상으로, 전체 서비스(Data Lake → DWH → Mart → Agent/Skill)를 전제한
**공통 데이터체계의 골격을 트리로 확정하고, 그 아래에 5개 보고서 조사에서 나온 실제 근거(살)를 매단**
작업이다. 개념 설명이 아니라 기계가 읽는 JSON과 오프라인 HTML 시각화가 산출물이다.

## 바로 보기

- `dist/index.html` — 단일 파일 시각화. 브라우저에서 열면 된다(외부 스크립트·네트워크 없음).
- `dist/skeleton.json` — 골격 + 근거를 합친 최종 데이터.

## 골격의 구성 (TGT v5 04장, PPT 슬라이드 12~13을 따름)

| 층 | 파일 | 내용 |
|---|---|---|
| 데이터 트리 | `skeleton/data_tree_template.json` | 사업보고서 서식 기준 포함 트리. L1 장(15) → L2 절 → L3 항목·표 유형(총 288노드). 주석은 '주제 유형' 31개. 업종 변형(보험)·조건부 항목을 scope로 표시 |
| 정보 트리 | `skeleton/info_tree.json` | 단일 부모 분류체계 v0. 11개 도메인, 90노드. 각 노드에 요구 스킬(종합·시계열·비교·FDD·Valuation) 배지 |
| 매핑 | `skeleton/mapping.json` | 데이터 노드 → 정보 노드. 주제 연결(topic) / 항목 대응 후보(item) 2수준, 266간선 |
| 관측 규약 | `skeleton/observation_schema.json` | 관측 한 건의 최소 설명 11필드, 문맥 유형 정규화(두 작성자의 상이한 어휘 통합), 상태 어휘, 비교 허용 순서 |
| 문서 맵 | `skeleton/dart_document_map.json` | DART 공시 문서 맵(A~J)과 서비스 4층에서 골격이 놓이는 자리 |

## 살 (근거)

- `inputs/derived/toc_all.json` — 5개 보고서의 wrapper 목차와 본문 앵커 위치.
- `inputs/derived/sections_findings.json` — 절 범위, 절별 표·셀·문단 수, 소제목, 그리고 발견 1,013건의 원문 위치 → 절 귀속.
- `inputs/derived/subheads_agg.json` — 절별 소제목을 5개 보고서에 걸쳐 집계(L3 근거).
- `inputs/derived/report_status.json` — 각 보고서의 조사 상태·커버리지·문맥 유형 빈도.
- `inputs/aggregate_a0002/`, `inputs/aggregate_a0001/` — 통합판 유형·규칙 후보(13개).

빌드는 발견을 가장 깊은 절의 템플릿 노드에 매달고, 규칙 후보를 지원 발견 경로로 노드에 연결하며,
보고서별 존재 여부(존재 / 제목만 / 상위 절에 포함 / 없음)를 오버레이한다.

## 두 가지 깊이

| 깊이 | 무엇을 보나 | 어디에 | 상태 |
|---|---|---|---|
| 의미 조사(초기 방식) | 셀 단위 역할·문맥·검산·반례 | `inputs/derived/sections_findings.json` (5건, 발견 1,013건) | 5건 모두 부분(paused/blocked), 재개하지 않음 |
| 구조 조사(현재 방식) | 목차 정렬, 절별 표·셀·문단 수, 소제목, 표 카탈로그(캡션·단위·기준일·머리글·행열·병합) | `inputs/reports/BRxxxx/structure.json` | 5건 완료, 15건 미취득 |

G01 나머지 15건은 골격 검증에 필요한 **구조 조사** 깊이로 진행한다. 절차와 가설은 `NEXT_ACTION.md`.
원문은 OpenDART API(`build/acquire_opendart.py`, 키는 `OPENDART_API_KEY` 환경변수)로 공시서류 원본 XML을 받아 `survey_structure.py --xml` 로 조사한다.
이 실행환경에서는 `dart.fss.or.kr`·`opendart.fss.or.kr` 접속이 조직 egress 정책으로 차단되어 실행하지 못했고, `inputs/reports/BRxxxx/identity.json` 에 슬롯·종목코드 참고값·예상 변형을 두었다. API 키와 내려받은 원문(`inputs/raw/`)은 커밋하지 않는다.

## 재현

```bash
python3 build/author_skeleton.py                 # skeleton/*.json
python3 build/survey_structure.py BRxxxx --html … --wrapper …   # inputs/reports/BRxxxx/structure.json (보고서별)
python3 build/build.py                           # dist/skeleton.json
python3 build/render_html.py                     # dist/index.html
```
초기 5건은 `sh build/survey_initial_five.sh` (원문 패키지 경로를 E 로 지정).

## 확정과 초안의 경계

- 확정: L1·L2 구조(5개 보고서 목차에서 동일 확인, 보험업 II장만 변형), 2수준 매핑 원칙, 발견의 절 귀속.
- 초안: L3 항목·표 유형(5개 보고서 소제목 관찰 + 서식 지식), 정보 트리 v0, API/XBRL 대응 표시(OpenDART 명세 참조, 미검증), 주석 주제 키워드 대응.
- 5개 표본은 모두 전수 의미조사 미완료(3 paused, 2 blocked)이며 통계적 대표성이 없다. 다른 업종(은행·증권·건설·지주 등)의 서식 변형은 미관찰.

근거 보고서: 삼성전자 2024(BR0001), DB손해보험 2023(BR0044), 셀트리온 2023(BR0053), 선바이오 2021(BR0016), NH프라임리츠 2021(BR0020).
원문 HTML과 단건 8종 산출물은 이 저장소에 포함하지 않는다(별도 패키지 보관).
