async def extract_youtube_transcript(url: str) -> str:
    _ = url
    return ""


async def detect_visual_segments(transcript: str, llm=None) -> list[dict]:
    _ = (transcript, llm)
    return []


async def extract_video_frames(url: str, timestamps: list[float]) -> list[dict]:
    _ = (url, timestamps)
    return []
