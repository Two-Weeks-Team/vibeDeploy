# Task 162: 스트리밍 트랜스크립트 추출 (v2)
상태: 미구현 | Phase 0 | 예상 시간: 6h
의존성: 161

## 1. 태스크 정의
v2에서는 대량 배치가 아닌, 한 영상씩 스트리밍 방식으로 트랜스크립트를 추출합니다. `youtube-transcript-api`를 기본으로 사용하며, 실패 시 `yt-dlp` 메타데이터 폴백을 지원합니다. 추출 완료 시 SSE 이벤트를 발행하여 실시간 피드에 표시합니다.

## 2. 수용 기준 (Acceptance Criteria)
- [ ] AC-1: 단일 영상 ID에 대해 트랜스크립트(텍스트)를 성공적으로 추출함.
- [ ] AC-2: 추출 시작(`zp.transcript.start`) 및 완료(`zp.transcript.complete`) 시 SSE 이벤트를 발행함.
- [ ] AC-3: IP 차단 또는 자막 부재 시 `yt-dlp`를 통해 제목/설명 메타데이터만이라도 추출하는 폴백 로직 구현.
- [ ] AC-4: 추출된 텍스트의 토큰 수를 계산하여 로그에 포함함.

## 3. 변경 대상 파일
- `agent/tools/youtube_transcript.py` (v2 업데이트)
- `agent/sse.py` (이벤트 타입 확인)

## 4. 상세 구현

### Streaming Transcript Extractor (agent/tools/youtube_transcript.py)
```python
from youtube_transcript_api import YouTubeTranscriptApi
from agent.sse import format_sse

async def extract_transcript_streaming(video_id: str):
    # 1. zp.transcript.start SSE 발행
    # 2. YouTubeTranscriptApi.get_transcript(video_id)
    # 3. 성공 시 텍스트 결합 및 zp.transcript.complete SSE 발행
    # 4. 실패 시 yt-dlp 폴백 및 메타데이터 반환
    pass
```

## 5. 테스트 계획
- `test_extract_success`: 자막이 있는 영상 ID로 텍스트 추출 성공 확인.
- `test_extract_fallback`: 자막이 없는 영상에서 메타데이터 폴백 동작 확인.
- `test_sse_emission`: 추출 과정에서 SSE 이벤트가 올바른 형식으로 발행되는지 확인.

## 6. 검증 방법
- `pytest agent/tests/test_youtube_transcript.py` 실행.
- SSE 로그를 통해 `zp.transcript.complete` 이벤트와 데이터가 일치하는지 확인.

## 7. 롤백 계획
- `git checkout docs/reference/162-streaming-transcript.md`
- `agent/tools/youtube_transcript.py` 변경 사항 취소.
