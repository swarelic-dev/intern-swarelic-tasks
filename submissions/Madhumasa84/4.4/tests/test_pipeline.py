"""
tests/test_pipeline.py — Unit tests for STT + LLM Mini Pipeline
"""
import pytest
from pathlib import Path
from pipeline import transcribe, generate_reply, run_pipeline


def test_transcribe_mock():
    audio_path = Path(__file__).parent.parent / "sample_audio.wav"
    transcript = transcribe(str(audio_path), mock=True)
    assert isinstance(transcript, str)
    assert len(transcript) > 0
    assert "appointment" in transcript.lower() or "smith" in transcript.lower()


def test_generate_reply_mock():
    transcript = "Can I book a meeting for Monday?"
    reply = generate_reply(transcript, mock=True)
    assert isinstance(reply, str)
    assert len(reply) > 0
    assert "smith" in reply.lower() or "delighted" in reply.lower() or "appointment" in reply.lower()


def test_run_pipeline_end_to_end():
    audio_path = Path(__file__).parent.parent / "sample_audio.wav"
    result = run_pipeline(str(audio_path), mock=True)
    assert "transcript" in result
    assert "reply" in result
    assert len(result["transcript"]) > 0
    assert len(result["reply"]) > 0
