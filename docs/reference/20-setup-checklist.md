# vibeDeploy 구현 사전 셋업 체크리스트

확정일: 2026-03-17
상태: **구현 시작 전 완료 필수**

---

## 1. 외부 LLM API 키 (직접 호출)

| # | 서비스 | 환경변수 | 발급 URL | 용도 | 상태 |
|---|--------|---------|---------|------|------|
| 1 | **Google AI (Gemini)** | `GOOGLE_API_KEY` | https://aistudio.google.com/apikey | Zero-Prompt 탐색 (`gemini-3.1-flash-lite-preview`) | ⬜ 필요 |
| 2 | **OpenAI** | `OPENAI_API_KEY` | https://platform.openai.com/api-keys | 코드 생성/계획 (`gpt-5.4`) | ⬜ 필요 |
| 3 | **Anthropic** | `ANTHROPIC_API_KEY` | https://console.anthropic.com/settings/keys | 코드 생성 (`claude-sonnet-4-6`) | ⬜ 확인 필요 (기존 키 유효?) |

## 2. DigitalOcean 계정 & 프로젝트

| # | 항목 | 환경변수 | 확인 방법 | 상태 |
|---|------|---------|---------|------|
| 4 | **DO Personal Access Token** | `DIGITALOCEAN_ACCESS_TOKEN` | DO 콘솔 → API → Personal Access Tokens | ⬜ 확인 필요 |
| 5 | **DO Project ID** | — | `doctl projects list` | ⬜ 확인 필요 |
| 6 | **$200 크레딧 적용** | — | https://mlh.link/digitalocean-signup | ⬜ 확인 필요 |

## 3. DO Gradient AI Platform

| # | 항목 | 환경변수 / 설정 | 확인 방법 | 상태 |
|---|------|---------------|---------|------|
| 7 | **Gradient Model Access Key** | `GRADIENT_MODEL_ACCESS_KEY` | DO 콘솔 → Gradient AI → API Keys | ⬜ 확인 필요 |
| 8 | **ADK 설치 확인** | — | `pip show gradient-adk` (≥0.0.8) | ⬜ 확인 |
| 9 | **gradient CLI 설치** | — | `gradient --version` | ⬜ 확인 |
| 10 | **Knowledge Base 생성** | `VIBEDEPLOY_KB_ID` | DO 콘솔 → Gradient AI → Knowledge Bases → 신규 생성 | ⬜ 생성 필요 |
| 11 | **KB 데이터 소스 연결** | — | DO 문서 + 프레임워크 패턴을 KB에 연결 | ⬜ 구성 필요 |
| 12 | **Agent Guardrails 설정** | — | DO 콘솔 → Gradient AI → Guardrails | ⬜ 설정 필요 |
| 13 | **Agent Evaluation Dataset** | — | `evaluations/test_cases.csv` 작성 | ⬜ 작성 필요 |

## 4. DO App Platform

| # | 항목 | 환경변수 / 설정 | 확인 방법 | 상태 |
|---|------|---------------|---------|------|
| 14 | **App ID** | `DO_APP_ID` | `doctl apps list` | ⬜ 확인 필요 |
| 15 | **App Platform 환경변수** | — | DO 콘솔 → App Platform → Settings → App-Level Environment Variables | ⬜ 확인 |
| 16 | **커스텀 도메인** | — | 선택사항 | ⬜ 선택 |

## 5. DO Spaces (Object Storage)

| # | 항목 | 환경변수 | 확인 방법 | 상태 |
|---|------|---------|---------|------|
| 17 | **Spaces Access Key** | `SPACES_ACCESS_KEY_ID` | DO 콘솔 → API → Spaces Keys | ⬜ 생성 필요 |
| 18 | **Spaces Secret Key** | `SPACES_SECRET_ACCESS_KEY` | 위와 동일 | ⬜ 생성 필요 |
| 19 | **Spaces Bucket 생성** | `SPACES_BUCKET_NAME` | `doctl spaces create vibedeploy-artifacts --region nyc3` | ⬜ 생성 필요 |
| 20 | **Spaces Endpoint** | `SPACES_ENDPOINT` | `https://nyc3.digitaloceanspaces.com` | ⬜ 확인 |

## 6. 검색 API (Zero-Prompt)

| # | 서비스 | 환경변수 | 발급 URL | 상태 |
|---|--------|---------|---------|------|
| 21 | **YouTube Data API v3** | `YOUTUBE_DATA_API_KEY` | https://console.cloud.google.com/apis/library/youtube.googleapis.com | ⬜ 필요 |
| 22 | **Brave Search** | `BRAVE_API_KEY` | https://brave.com/search/api/ (무료 2,000건/월) | ✅ 확보됨 |
| 23 | **Exa Search** | — | API 키 불필요 (토큰 자동 발급) | ✅ 불필요 |
| 24 | **OpenAlex** | — | API 키 불필요 (polite pool: 이메일만 헤더에) | ✅ 불필요 |
| 25 | **arXiv** | — | API 키 불필요 | ✅ 불필요 |

## 7. GitHub

| # | 항목 | 환경변수 | 확인 방법 | 상태 |
|---|------|---------|---------|------|
| 26 | **GitHub PAT (생성 앱 레포용)** | `GITHUB_TOKEN` | GitHub → Settings → Developer settings → PAT | ⬜ 확인 필요 |
| 27 | **GitHub Organization** | — | `Two-Weeks-Team` | ✅ 확인됨 |

## 8. Docker (빌드 검증용)

| # | 항목 | 확인 방법 | 상태 |
|---|------|---------|------|
| 28 | **Docker Desktop / Docker Engine** | `docker --version` | ⬜ 확인 필요 |
| 29 | **Docker 소켓 접근** | `docker ps` 실행 가능 여부 | ⬜ 확인 필요 |
| 30 | **node:20-slim 이미지** | `docker pull node:20-slim` | ⬜ 사전 pull |
| 31 | **python:3.12-slim 이미지** | `docker pull python:3.12-slim` | ⬜ 사전 pull |

## 9. Python 의존성 (agent/)

| # | 패키지 | 용도 | 설치 |
|---|--------|------|------|
| 32 | `gradient-adk>=0.0.8` | DO ADK | ✅ 기존 |
| 33 | `google-genai` | Gemini 직접 호출 | ⬜ 추가 필요 |
| 34 | `openai` | OpenAI 직접 호출 | ✅ 기존 |
| 35 | `anthropic` | Anthropic 직접 호출 | ✅ 기존 |
| 36 | `docker` | Docker SDK (빌드 검증) | ⬜ 추가 필요 |
| 37 | `boto3` 또는 `aioboto3` | DO Spaces (S3 호환) | ⬜ 추가 필요 |
| 38 | `youtube-transcript-api` | 트랜스크립트 추출 | ⬜ 추가 필요 |
| 39 | `google-api-python-client` | YouTube Data API | ⬜ 추가 필요 |

## 10. npm 의존성 (web/)

| # | 패키지 | 용도 | 설치 |
|---|--------|------|------|
| 40 | `@dnd-kit/core` | 칸반 드래그 앤 드롭 | ⬜ 추가 필요 |
| 41 | `vitest` + `@testing-library/react` | 프론트엔드 테스트 | ⬜ 추가 필요 |

---

## 요청 사항 (사용자 확인/조치 필요)

### 즉시 확인 필요

```bash
# 1. DO 계정 상태 확인
doctl account get

# 2. 기존 앱 확인
doctl apps list

# 3. Gradient AI 키 확인
echo $GRADIENT_MODEL_ACCESS_KEY

# 4. Docker 확인
docker --version && docker ps

# 5. ADK 버전 확인
pip show gradient-adk
```

### 사용자가 직접 수행해야 할 작업

| # | 작업 | 위치 | 예상 시간 |
|---|------|------|---------|
| **S1** | Google AI API 키 발급 | https://aistudio.google.com/apikey | 2분 |
| **S2** | YouTube Data API 활성화 + 키 발급 | Google Cloud Console | 5분 |
| **S3** | DO Knowledge Base 생성 | DO 콘솔 → Gradient AI | 10분 |
| **S4** | DO Spaces Bucket 생성 | DO 콘솔 → Spaces | 3분 |
| **S5** | DO Spaces Access Key 생성 | DO 콘솔 → API → Spaces Keys | 2분 |
| **S6** | OpenAI API 키 확인/갱신 | https://platform.openai.com/api-keys | 2분 |
| **S7** | Anthropic API 키 확인/갱신 | https://console.anthropic.com | 2분 |
| **S8** | Docker Desktop 설치 (미설치 시) | https://docker.com/products/docker-desktop | 10분 |
| **S9** | Docker 이미지 사전 pull | 터미널 | 5분 |

### .env.production 템플릿

```bash
# === 외부 LLM API (직접 호출) ===
GOOGLE_API_KEY=
OPENAI_API_KEY=
ANTHROPIC_API_KEY=

# === DigitalOcean ===
DIGITALOCEAN_ACCESS_TOKEN=
GRADIENT_MODEL_ACCESS_KEY=
DO_APP_ID=

# === DO Spaces ===
SPACES_ACCESS_KEY_ID=
SPACES_SECRET_ACCESS_KEY=
SPACES_BUCKET_NAME=vibedeploy-artifacts
SPACES_ENDPOINT=https://nyc3.digitaloceanspaces.com

# === DO Gradient AI ===
VIBEDEPLOY_KB_ID=

# === 검색 API ===
YOUTUBE_DATA_API_KEY=
BRAVE_API_KEY=

# === GitHub ===
GITHUB_TOKEN=
```
