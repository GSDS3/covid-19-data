# 다음 행동 — G01 나머지 15건을 골격에 매달기

## 현재 상태 (2026-09-17)

- 골격 v0.2: 데이터 트리 288노드 · 정보 트리 90노드 · 매핑 266간선 · 관측 규약.
- 구조 조사 완료 5건(삼성전자 2024, DB손해보험 2023, 셀트리온 2023, 선바이오 2021, NH프라임리츠 2021). 표 유형 1,200여 개, 보고서 2건 이상 공통 유형 140여 개.
- 미취득 15건: `inputs/reports/BRxxxx/identity.json` 슬롯만 있음. 이 실행환경은 `dart.fss.or.kr`, `opendart.fss.or.kr`, `kind.krx.co.kr` 접속이 조직 egress 정책으로 차단됨(403 CONNECT). 우회하지 않았다.

## 깊이 조정 (사용자 지시에 따른 결정)

나머지 15건은 **구조 조사**만 한다. 목차 정렬, 절별 표·셀·문단 수, 소제목, 표 카탈로그(캡션·단위·기준일·머리글·행열·병합)까지.
셀 단위 의미 판별(초기 5건 방식, 보고서당 수만 셀)은 골격이 안정된 뒤 **표 유형 단위**로 재개한다.
이유: 지금 목적은 골격의 검증·확장이며, 그 검증에 필요한 정보는 절 구성·표 유형·머리글이지 개별 셀의 문맥이 아니다.

## 보고서 1건을 매다는 절차

1. 원문 취득(DART 접근이 되는 환경에서): 뷰어 wrapper(`https://dart.fss.or.kr/dsaf001/main.do?rcpNo=…`)와 본문 문서 HTML.
   초기 5건 패키지의 `evidence/BRxxxx/wrapper.html`, `evidence/BRxxxx/acquisition.json`(wrapper_toc), `html/BRxxxx_*.html` 형식이면 그대로 쓸 수 있다.
2. 구조 조사:
   ```bash
   python3 build/survey_structure.py BR0043 --html html/BR0043_2023_001720_신영증권.html \
       --wrapper evidence/BR0043/wrapper.html --company 신영증권 --year 2023 \
       --receipt <접수번호> --sector "금융(증권)" --period "2022-04-01~2023-03-31"
   ```
   `--wrapper` 대신 `--acquisition evidence/BR0043/acquisition.json` 도 된다.
3. `python3 build/build.py && python3 build/render_html.py` → `dist/index.html` 갱신.
4. `structure.json` 의 `unmatched`(템플릿 미대응 목차 항목)와 시각화 ⑥ 탭의 'L3 개정 후보'를 보고 `build/author_skeleton.py` 의 템플릿(별칭·업종 변형·L3 항목)을 개정한 뒤 1~3을 재실행한다.

## 15건에서 확인할 골격 가설 (identity.json 의 expected_variants)

- 신영증권 2023·2025: II장 금융업 서식(증권) → F1~F4에 '증권' 별칭 필요 여부, 3월 결산 기간 문맥.
- 삼성스팩4호 2021: 빈 절 다수, 설립 후 첫 사업기간, 합병 관련 사후정보.
- 엑세스바이오 2025: 외국법인 특례 기재, 회계기준·통화 문맥.
- 대한항공 2021, 기아 2022, 현대자동차 2021, SK하이닉스 2022·2024, 하이트진로 2023, 대동 2024, 포스코 2021: 일반 서식 안의 업종별 표 변형(항공기 리스, 판매보증, 부문 병존, 재고·설비, 주세, 지주 전환).
- 삼성화재 2025: 보험업 F1~F4 재사용 검증(2025년 서식 변경 여부).
- 한국전력공사 2023: 공기업(정부 최대주주, 요금 규제, 발전자회사).
- 현대건설 2022: III.8.04 수주계약 현황(진행률) 표, XI.2 우발채무.

## 하지 않은 것

- 원문 없는 상태에서 15건의 절 구성·표 유형을 추정해 채우지 않았다.
- 초기 5건의 의미조사(paused/blocked)를 재개하지 않았다.
