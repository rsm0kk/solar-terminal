# SOLAR ANALYST TERMINAL — 태양광 섹터 대시보드

태양광 밸류체인(폴리실리콘 → 웨이퍼 → 셀 → 모듈 → 발전·PPA)과
**OCI홀딩스 · 한화솔루션 · HD현대에너지솔루션 · SK이터닉스** 4사를
매일 자동으로 수집·검증해서 **HTML 파일 하나**로 찍어내는 프로젝트입니다.

파이썬이 데이터를 긁어 → 정규화·품질검사 → 누적 저장 → 단일 HTML 생성.
그 HTML 하나만 열거나 공유하면 됩니다. 인터넷 없이도 열립니다.

---

## 1. 5분 안에 실행하기

```bash
pip install -r requirements.txt
```

```bash
python scripts/update_all.py
```

끝입니다. `out/태양광_대시보드_최신.html` 이 생기고 브라우저로 열면 됩니다.

**API 키가 하나도 없어도 동작합니다.** 키가 필요한 소스만 화면의
"데이터 상태" 탭에 `API 미설정` 으로 표시되고 나머지는 정상 수집됩니다.

Windows 사용자는 이 스크립트를 더블클릭해도 됩니다:

```bash
powershell -ExecutionPolicy Bypass -File "scripts\run_local_update.ps1"
```

---

## 2. 지금 실제로 연결된 데이터

2026-07-26 기준, 실제 호출로 동작을 확인한 것만 적었습니다.

### 키 없이 바로 되는 것 (5개)

| 소스 | 내용 | 주기 | 라이선스 |
|---|---|---|---|
| **Our World in Data** | 국가별 태양광 발전량·설비용량·전력믹스 비중 | 연간 | CC BY 4.0 |
| **Ember** | 월간 국가별 태양광 발전량·전력수요 (6개국) | 월간 | CC BY-SA 4.0 |
| **Open-Meteo** | 국내 7개 권역 일사량 실측·예보 | 일간 | CC BY 4.0 |
| **NASA POWER** | 일사량 장기평년 + 독립 실측 (교차검증용) | 일간 | public domain |
| **네이버 금융** | 4사 주가·거래량·외국인소진율 | 영업일 | 공개 시세 |

> Ember REST API 는 2026년부터 키를 요구합니다(403). 이 프로젝트는 Ember 가
> 공식 배포하는 **공개 다운로드 CSV** 를 씁니다. 잠금 데이터를 우회하는 게 아닙니다.

### 보유한 키로 이미 되는 것

| 소스 | 내용 | 환경변수 |
|---|---|---|
| **OpenDART** | 4사 공시 목록 + 분기 매출·영업이익·순이익·순차입금 | `DART_API_KEY` |
| **FRED** | 원/달러·위안/달러 환율 | `FRED_API_KEY` |

### 키를 넣으면 살아나는 것

| 소스 | 내용 | 지금 상태 |
|---|---|---|
| **EIA** | 미국 태양광 발전량·설비용량 | `EIA_API_KEY` 미설정 |
| **KPX (공공데이터포털)** | 육지·제주 SMP, REC 현물가·거래량 | 키는 유효하나 **활용신청 필요** (아래 참고) |

### 자동 수집하지 않는 것 — 수기 입력으로 대체

폴리실리콘·웨이퍼·셀·모듈 **스팟 가격**은 InfoLink·TrendForce·Bernreuter·pvXchange 등
유료 구독이거나 이용약관상 자동수집이 불명확합니다. **우회하지 않습니다.**
`data/manual/solar_supply_chain_prices.csv` 에 옮겨 적으면 다음 실행에서 자동 반영됩니다.

기업 IR KPI, 애널리스트 컨센서스, 데이터센터 PPA 계약, 생산능력 파이프라인도 마찬가지입니다.

---

## 3. API 키 발급

`.env.example` 를 `.env` 로 복사한 뒤 값을 채웁니다. `.env` 는 git 에 올라가지 않습니다.

```bash
copy .env.example .env
```

### EIA (권장, 무료·즉시)

https://www.eia.gov/opendata/register.php 에서 이메일만 넣으면 바로 받습니다.
미국 태양광 발전량·설비용량이 채워지고, 한화솔루션 Qcells 분석의 핵심 축이 살아납니다.

### 공공데이터포털 — SMP·REC (중요)

**새 키 발급이 아닙니다.** 이미 쓰고 계신 data.go.kr 키는 유효합니다
(관세청 API 는 200 정상 응답). data.go.kr 은 **API 마다 개별 '활용신청'** 이
필요한데 KPX API 가 아직 미승인이라 500 이 떨어집니다.

1. https://www.data.go.kr 로그인
2. "한국전력거래소 계통한계가격(SMP)" 검색 → **활용신청**
3. REC 관련 API 도 같이 신청
4. 개발계정은 보통 즉시 승인 → 승인되면 **같은 키가 그대로** 동작합니다

이게 승인되면 국내 전력시장 탭 전체와 SK이터닉스 시그널이 살아납니다.

### 이미 있는 키

`DART_API_KEY`, `FRED_API_KEY` 는 기존 전력기기 대시보드의 `secrets.json` 을
자동으로 찾아 재사용합니다. `.env` 에 직접 적어도 됩니다.

### 필요 없는 것

- **KRX / 한국투자증권(KIS)** — 주가는 네이버 금융으로 이미 커버됩니다
- **Ember API 키** — 공개 CSV 로 해결됩니다

---

## 4. 실행 명령

| 명령 | 하는 일 |
|---|---|
| `python scripts/update_all.py` | 전체 수집 → 검증 → JSON → HTML |
| `python scripts/update_all.py --as-of 2026-07-26` | 기준일 지정 |
| `python scripts/update_all.py --only dart,naver_stock` | 특정 소스만 수집 |
| `python scripts/update_all.py --no-fetch` | 수집 생략, 저장된 데이터로 다시 빌드만 |
| `python scripts/update_all.py --no-render` | JSON 까지만 (HTML 생략) |
| `python scripts/update_all.py --traceback` | 실패 시 스택 출력 |
| `python scripts/validate_data.py` | 데이터 정합성 검사 (빌드와 별개) |
| `python -m pytest tests -q` | 테스트 38개 |

소스 이름은 `config/sources.yaml` 의 최상위 키입니다
(`owid_solar`, `ember_monthly`, `openmeteo_solar`, `nasa_power`, `naver_stock`,
`dart`, `fred`, `eia`, `kpx`, `supply_chain_prices`, ...).

---

## 5. 화면 구성

| 탭 | 내용 |
|---|---|
| **오늘의 결론** | 가장 중요한 변화 3개, 기업별 시그널 점수, 아침 브리핑 |
| **공급망 가격** | 폴리실리콘→웨이퍼→셀→모듈 스몰멀티플, 변화율, 노출 기업 히트맵 |
| **글로벌 수요** | 국가별 월간 발전량·설비용량·태양광 비중, 미국 지표 |
| **국내 전력시장** | SMP·REC·SMP+REC 환산수익, 권역별 일사량·평년대비 |
| **데이터센터·PPA** | 확정/기대 계약 분리 집계, 연도별·구매자별, 계약 목록 |
| **기업 모니터** | 4사별 주가·실적·시그널 기여도·공시, 밸류체인 노출도 |
| **밸류에이션** | 기업별 핵심 멀티플. 컨센서스 없으면 '데이터 없음' |
| **뉴스·공시** | DART 공시 목록 (정렬·검색) |
| **데이터 상태** | 소스별 기준일·마지막 수집·발표주기·다음 갱신·품질 보고서 |

공통: 다크/라이트 전환, 전체 검색, CSV 다운로드, 기간 선택(1M~전체),
범례 클릭 토글, 차트 툴팁에 값·단위·기준일·출처 표시.

---

## 6. 자동 갱신

### GitHub Actions (매일 06:30 KST)

`.github/workflows/update-dashboard.yml` 이 이미 들어 있습니다.

```yaml
- cron: "30 21 * * *"   # 21:30 UTC = 06:30 KST (다음날)
```

GitHub Actions 의 cron 은 **UTC 기준**이라 한국시간 06:30 은 `21:30 UTC` 입니다.
시간을 바꾸려면 원하는 KST 시각에서 9시간을 빼세요.

**저장소 설정 순서**

1. GitHub 에 저장소를 만들고 이 폴더를 push
2. Settings → Secrets and variables → Actions → New repository secret
   에서 `DART_API_KEY`, `FRED_API_KEY`, `EIA_API_KEY`,
   `DATA_GO_KR_SERVICE_KEY` 등록
3. Settings → Pages → Source 를 **GitHub Actions** 로 설정
4. Actions 탭에서 `workflow_dispatch` 로 수동 실행해 확인

배포되면 `https://<사용자명>.github.io/<저장소명>/` 에서 열립니다.
누적 데이터(`data/history`)는 캐시 + 커밋으로 유지되므로 시계열이 계속 쌓입니다.

### Windows 작업 스케줄러

작업 스케줄러 → 작업 만들기 → 트리거 매일 06:30 → 동작 "프로그램 시작"

- 프로그램: `powershell.exe`
- 인수: `-ExecutionPolicy Bypass -File "scripts\run_local_update.ps1"`
- 시작 위치: 이 프로젝트 폴더 경로

### Linux / macOS cron

```bash
30 6 * * * cd /path/to/태양광\ 대시보드 && /usr/bin/python3 scripts/update_all.py >> data/logs/cron.log 2>&1
```

---

## 7. 수기 입력하기

`data/manual/` 의 CSV 5개를 채우면 다음 실행에서 자동 반영됩니다.

| 파일 | 용도 | 주기 |
|---|---|---|
| `solar_supply_chain_prices.csv` | 폴리실리콘·웨이퍼·셀·모듈 가격 | 주 1회 |
| `company_kpi_manual.csv` | 생산능력·가동률·출하량·부문실적 | 분기 |
| `manual_estimates.csv` | 컨센서스·목표주가 | 분기 |
| `ppa_deals_manual.csv` | 데이터센터향 PPA 계약 | 수시 |
| `company_capacity_pipeline.csv` | 공장·프로젝트 파이프라인 | 분기 |

각 파일 맨 위 `#` 주석에 **필드 설명·단위·날짜 형식·중복 판단키·필수 여부**가 들어 있습니다.

**중요한 규칙 두 가지**

- `row_type` 이 `SAMPLE` 인 행은 입력 예시입니다. 대시보드에 **절대 포함되지 않습니다.**
  실제 데이터는 `DATA` 로 적으세요.
- PPA 계약에서 `official=0`(언론보도·추정)은 확정 집계에서 **제외**되고
  화면에 "기대·추정"으로만 표시됩니다. 캡티브 기대물량을 확정에 넣지 마세요.

가격을 입력하면 비중국산 프리미엄, 셀→모듈 스프레드, 미국-중국 가격차가
**자동으로 계산**되고 OCI·한화·HDES 시그널이 살아납니다.

---

## 8. 데이터 오류 확인하기

```bash
python scripts/validate_data.py
```

- 화면 **"데이터 상태"** 탭에 소스별 상태와 품질 보고서가 그대로 나옵니다
- `public/data/quality_report.json` 에 전체 이슈 목록
- `public/data/status.json` 에 소스별 수집 결과

### 자동으로 검사하는 것

중복 · 날짜 역전 · 미래 날짜 · 비정상 급등락 · 단위 오류 · 불가능한 음수 ·
통화 환산 기준일 · **누적→단독분기 변환 검증** · 동일 출처의 과거값 수정 ·
출처 간 값 충돌 · 공개 CSV 구조 변경(필수 필드·행수)

### 설계 원칙

- **수집 실패가 기존 정상 데이터를 덮어쓰지 않습니다.** 0 이나 null 로 채우지 않고
  마지막 정상값을 유지한 채 `stale` 로 표시합니다
- 소스 하나가 죽어도 나머지 수집은 계속됩니다 (부분 실패 허용)
- 출처가 다른 수치를 **임의로 합성하지 않습니다.** 신뢰도가 높은 쪽을 메인으로 쓰고
  충돌 사실을 품질 보고서에 남깁니다
- 랜덤·더미 숫자를 실데이터처럼 표시하지 않습니다. 없으면 "데이터 없음"과 설정 방법을 보여줍니다

---

## 9. 폴더 구조

```
scripts/
  update_all.py           수집→검증→빌드 전체 파이프라인
  validate_data.py        정합성 검사
  run_local_update.ps1    Windows 실행·스케줄러용
  core/
    model.py              DataPoint (출처·기준일·단위 없는 값은 만들 수 없음)
    store.py              증분 저장, 수정 감지, 결측 덮어쓰기 방지
    quality.py            품질검사
    runner.py             소스 순회 수집 (부분 실패 허용)
    derive.py             파생지표 (프리미엄·스프레드·SMP+REC·영업이익률)
    signals.py            시그널 엔진
    brief.py              아침 브리핑 (규칙 기반, LLM 미사용)
    dashboard.py          dashboard.json 조립
    template.py           HTML 템플릿
    render.py             HTML 빌드
    records.py            공시·PPA 등 비시계열 레코드 영속 저장
  adapters/               소스별 독립 수집기 10종
config/
  sources.yaml            소스 레지스트리 (등급·주기·staleness·필요 키)
  companies.yaml          4사 정의 + 밸류체인 노출도
  metrics.yaml            지표 사전 (단위·축그룹·주기)
  signals.yaml            시그널 규칙 + 기업별 가중치
data/
  history/points.parquet  누적 시계열 (지우지 마세요)
  processed/              공시·PPA·평년값
  manual/                 수기 입력 CSV 5종
  raw/, .cache/           원본·캐시 (재다운로드 가능, git 제외)
public/data/              dashboard.json, status.json, quality_report.json, morning_brief.json
out/                      완성된 HTML  <- 이것만 공유
tests/                    테스트 38개
```

---

## 10. 시그널 엔진

각 지표의 변화율을 -2 ~ +2 로 점수화하고 기업별 가중합을 냅니다.
가중치는 `config/signals.yaml` 에서 직접 수정할 수 있습니다.

```yaml
weights:
  oci:
    poly_premium_widening: 3.0    # 비중국 프리미엄 확대 → OCI 긍정
    china_poly_rebound: 2.0
  hanwha:
    us_module_price_up: 3.0
    china_poly_rebound: -0.5      # 음수 = 원가 상승 요인
```

점수 하나로 단정하지 않습니다. 화면에는 **총점 · 전주 대비 변화 · 점수를 움직인
상위 3개 지표 · 데이터가 오래돼 제외된 지표 · 신뢰도**가 함께 나옵니다.

> 시그널 점수는 방향성 참고치이며 실적 확정치나 투자 권유가 아닙니다.

---

## 11. 알아두면 좋은 것

**SMP+REC 환산수익**은 `SMP + REC × 가중치 ÷ 1000` 입니다.
1 REC = 1MWh 단순 환산에 가중치 기본값 1.0 을 적용한 **시장가격 기반 참고치**로,
실제 계약수익과 다릅니다. 가중치는 프로젝트마다 다릅니다.

**분기 실적**은 DART 누적 손익계산서를 직전분기 차감으로 환산한 단독분기입니다
(4Q = 연간 − 3Q누적). 재무상태표 항목은 분기말 잔액이라 차분하지 않습니다.
변환 결과는 "단독분기 4개 합 = 연간 누적" 으로 매번 검증합니다.

**일사량**은 실측과 예보를 구분해 저장합니다. 예보분에는 '추정' 배지가 붙습니다.
Open-Meteo 와 NASA POWER 는 서로 다른 위성·모델이라 값이 갈리는 게 정상이며,
품질 보고서에 참고(info) 등급으로만 남습니다.

**SSL 인증서 오류**가 뜨면서 자동 재시도되는 건 이 PC 의 백신·프록시가
SSL 트래픽을 검사하기 때문입니다. 해당 호스트에 한해서만 검증을 끄고 재시도합니다.

---

## 12. 출처와 라이선스

| 소스 | 라이선스 | 주의 |
|---|---|---|
| Our World in Data | CC BY 4.0 | 출처 표기 필요 |
| Ember | CC BY-SA 4.0 | 출처 표기 + 동일조건 |
| Open-Meteo | CC BY 4.0 | 비상업 무료. 대량 호출 금지 |
| NASA POWER | public domain | 제한 없음 |
| OpenDART / KPX / EIA | 각 기관 이용약관 | 키 발급 시 동의한 범위 내 |
| 네이버 금융 | 공개 시세 | **1일 1회만 조회.** 대량·고빈도 호출 금지 |
| InfoLink·TrendForce·Bernreuter·pvXchange | 유료·구독 | **자동수집 안 함.** 수기 입력만 |

기사·리포트 전문을 저장하지 않습니다. 제목·날짜·링크·직접 작성한 요약만 남깁니다.
API 키는 코드·HTML 어디에도 들어가지 않습니다. `.env` 와 GitHub Secrets 로만 관리합니다.
