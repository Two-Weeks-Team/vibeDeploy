from zero_prompt.events import (
    ZP_BUILD_QUEUED,
    ZP_BUILD_START,
    ZP_CARD_PASSED,
    ZP_SESSION_ERROR,
    ZP_SESSION_PAUSE,
    ZP_SESSION_RESUME,
    ZP_VIDEO_START,
    build_queued_event,
    build_start_event,
    card_passed_event,
    session_error_event,
    session_pause_event,
    session_resume_event,
    video_start_event,
)


def test_session_pause_event():
    ev = session_pause_event("s1")
    assert ev["type"] == ZP_SESSION_PAUSE
    assert ev["session_id"] == "s1"


def test_session_resume_event():
    ev = session_resume_event("s2")
    assert ev["type"] == ZP_SESSION_RESUME
    assert ev["session_id"] == "s2"


def test_session_error_event():
    ev = session_error_event("s3", "timeout")
    assert ev["type"] == ZP_SESSION_ERROR
    assert ev["session_id"] == "s3"
    assert ev["error"] == "timeout"


def test_video_start_event():
    ev = video_start_event("s4", "vid-42")
    assert ev["type"] == ZP_VIDEO_START
    assert ev["session_id"] == "s4"
    assert ev["video_id"] == "vid-42"


def test_card_passed_event():
    ev = card_passed_event("s5", "card-7")
    assert ev["type"] == ZP_CARD_PASSED
    assert ev["session_id"] == "s5"
    assert ev["card_id"] == "card-7"


def test_build_queued_event():
    ev = build_queued_event("s6", "card-8")
    assert ev["type"] == ZP_BUILD_QUEUED
    assert ev["session_id"] == "s6"
    assert ev["card_id"] == "card-8"


def test_build_start_event():
    ev = build_start_event("s7", "card-9")
    assert ev["type"] == ZP_BUILD_START
    assert ev["session_id"] == "s7"
    assert ev["card_id"] == "card-9"
