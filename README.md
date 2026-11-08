# Python Basic Bloomberg Public

위키독스 책 10장에서 사용하는 스켈레톤 코드입니다.  
이 레포는 완성본이 아니라, 책을 따라가며 하나씩 구현해 나가는 샘플 코드입니다.

## 프로젝트 소개

이 프로젝트는 Streamlit으로 만드는 주식 분석·주문 워크스테이션입니다.

- 분석 화면에서 종목을 입력하고 기간을 선택합니다.
- 현재가, 기간 시세, 지표, 차트를 붙입니다.
- AI Copilot과 뉴스 브리핑을 연결합니다.
- 사이드바 주문 패널에서 주문 초안을 만들고 결과를 확인합니다.
- 마지막으로 GitHub에 프로젝트를 올려 정리합니다.

현재 레포는 스켈레톤 코드이므로, 여러 기능이 placeholder 상태로 남아 있습니다.

## 프로젝트 구조

```text
python-basic-bloomberg-public/
├── app.py
├── pages/
│   ├── 1_종목_분석실.py
│   └── 2_주문_보유현황.py
├── utils/
│   ├── ai_assistant.py
│   ├── analysis.py
│   ├── formatting.py
│   ├── kis_client.py
│   ├── navigation.py
│   ├── news_client.py
│   └── storage.py
├── scripts/
│   └── check_integrations.py
├── .env.example
└── requirements.txt
```

핵심 파일은 아래 정도만 먼저 보면 충분합니다.

- `app.py`: 앱 진입점
- `pages/1_종목_분석실.py`: 메인 분석 화면
- `pages/2_주문_보유현황.py`: 주문 상태, 미체결, 보유현황 화면
- `utils/analysis.py`: 시세 정리, 지표 계산, 주문 미리보기 요약
- `utils/kis_client.py`: KIS 시세·계좌 조회 및 모의 주문 연동
- `utils/ai_assistant.py`: OpenAI Copilot·뉴스 브리핑 연동
- `utils/news_client.py`: RSS 뉴스 수집
- `utils/storage.py`: Streamlit session state 초기화

## 실행 방법

### 1. 가상환경 생성

```bash
python -m venv .venv
source .venv/bin/activate
```

Windows라면 아래 명령을 사용합니다.

```bash
.venv\Scripts\activate
```

### 2. 패키지 설치

```bash
pip install -r requirements.txt
```

### 3. `.env` 준비

`.env.example`을 복사해서 `.env` 파일을 만듭니다.

그다음 `.env` 안의 값을 자신의 환경에 맞게 수정합니다.

```env
KIS_ENV=demo
KIS_APP_KEY=YOUR_KIS_APP_KEY
KIS_APP_SECRET=YOUR_KIS_APP_SECRET
KIS_ACCOUNT_NO=12345678
KIS_ACCOUNT_PRODUCT_CODE=01

OPENAI_API_KEY=YOUR_OPENAI_API_KEY
OPENAI_MODEL=gpt-5.4-mini
```

### 4. 연동 상태 점검

아래 스크립트로 KIS/OpenAI 설정 상태를 먼저 확인할 수 있습니다.

```bash
python scripts/check_integrations.py
```

### 5. Streamlit 실행

```bash
streamlit run app.py
```

실행하면 기본적으로 `종목 분석실` 화면으로 이동합니다.

## 현재 스켈레톤 상태

현재 레포는 학습용 뼈대이므로 아래 기능은 아직 완성되어 있지 않습니다.

- 실전 주문 요청

KIS 시세·계좌 조회, AI Copilot, RSS 뉴스, 모의투자 주문 요청은 설정이 있을 때 연결됩니다.
주문/보유현황 화면은 최근 주문, 미체결 주문, 보유 종목, 예수금을 KIS에서 조회합니다.

모의 주문은 `주문하기`를 누르면 한국투자증권 모의투자 계좌에 요청됩니다.
실전 주문은 지원하지 않으며 `KIS_ENV=real`일 때 주문 요청이 차단됩니다.

## 주의사항

- `.env` 파일은 Git에 올리지 않습니다.
- 학습 중에는 먼저 `demo` 기준으로 확인하는 것을 권장합니다.

## 권장 학습 방식

이 프로젝트는 VS Code Chat을 함께 활용하는 실습을 전제로 합니다.

- 먼저 현재 파일 구조를 읽습니다.
- Chat에게 한 번에 큰 기능 전체를 맡기기보다 작은 단위로 요청합니다.
- 실행 결과를 확인한 뒤, 부족한 부분을 다시 지시하며 다듬습니다.
- 코드가 생성되면 그대로 넘기지 말고 직접 읽고 검증합니다.

즉, 이 레포의 목적은 완성 코드를 받는 것이 아니라, AI와 함께 구현 과정을 밟는 것입니다.
