from pydantic import BaseModel, Field


class VideoCandidate(BaseModel):
    video_id: str
    title: str
    channel_title: str
    published_at: str
    view_count: int = 0
    like_count: int = 0
    comment_count: int = 0
    engagement_rate: float = 0.0
    category: str = ""
    description: str = ""
    thumbnail_url: str = ""
    duration: str = ""
    has_captions: bool = Field(default=False)
