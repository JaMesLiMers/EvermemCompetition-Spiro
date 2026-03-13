#!/usr/bin/env python3
"""Extract transcript from audio files using Gemini 3 Pro via uni-api.

Outputs structured JSON matching the EverMemOS basic_events dataset format:
  meta: { user_id, basic_event_id, basic_start_time, basic_end_time }
  object: { basic_transcript }
"""

import argparse
import base64
import json
import re
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

import httpx
from dotenv import load_dotenv
import os

# Load .env from the same directory as this script
ENV_PATH = Path(__file__).resolve().parent / ".env"
load_dotenv(ENV_PATH)

GEMINI_API_URL = "https://api.uniapi.io/gemini/v1beta/models/gemini-3-pro-preview:generateContent"
API_KEY = os.getenv("LLM_API_KEY")

TRANSCRIPTION_PROMPT = """请转录这段音频中的对话内容，并按照以下格式输出。

## 输出格式要求

请严格按照以下格式输出转录结果：

[Fragment 1: <开始时间 YYYY-MM-DD HH:MM> - <结束时间 YYYY-MM-DD HH:MM>]
标题: <这段对话的简短标题>
类型: <对话类型标签，如 career, social, home, self_awareness, interest 等>

[说话人1]: [语气/情绪标注] 说话内容

------------------------------------------

## 具体要求

1. **说话人标识**: 用 说话人1, 说话人2, 说话人3 等标识不同说话人，按出场顺序编号。如果能识别出性别，使用 说话人1/男 或 说话人1/女
2. **主用户**: 如果能识别出录音设备持有者（主用户），用 [用户] 标识
3. **不要添加时间戳**: 每句话前不需要 [MM:SS] 时间戳
4. **语气标注**: 在方括号中标注语气、情绪、语速等特征，如 [思考停顿]、[语速加快]、[肯定语气] 等
5. **Fragment 分段**: 如果话题有明显转换，分成多个 Fragment，每个 Fragment 有自己的标题和类型
6. **时间格式**: Fragment 的开始和结束时间用 "YYYY-MM-DD HH:MM" 格式（基于当前日期推算）
7. **如实转录**: 保留所有语气词、口头禅、停顿等
8. **语言**: 中文用中文，英文用英文

## 示例

[Fragment 1: 2026-03-13 10:00 - 2026-03-13 10:05]
标题: 关于产品设计方案的讨论
类型: career

[用户]: [平稳语气] 我们来看一下这个方案。
[说话人1/女]: [思考停顿] 嗯，我觉得这个方案还不错。
[说话人2/男]: [肯定语气] 对，我也是这么认为的。

------------------------------------------

请开始转录："""


def read_audio_as_base64(audio_path: str) -> tuple[str, str]:
    """Read audio file and return base64-encoded data and MIME type."""
    path = Path(audio_path)
    suffix = path.suffix.lower()
    mime_map = {
        ".mp3": "audio/mpeg",
        ".wav": "audio/wav",
        ".m4a": "audio/mp4",
        ".ogg": "audio/ogg",
        ".flac": "audio/flac",
        ".webm": "audio/webm",
    }
    mime_type = mime_map.get(suffix, "audio/mpeg")
    data = path.read_bytes()
    return base64.standard_b64encode(data).decode("utf-8"), mime_type


def call_gemini(prompt: str, audio_b64: str, mime_type: str) -> str:
    """Call Gemini 3 Pro API with audio data and return the response text."""
    if not API_KEY:
        print("Error: LLM_API_KEY not found in .env", file=sys.stderr)
        sys.exit(1)

    payload = {
        "contents": [
            {
                "parts": [
                    {"inline_data": {"mime_type": mime_type, "data": audio_b64}},
                    {"text": prompt},
                ],
                "role": "user",
            }
        ],
    }

    headers = {
        "Content-Type": "application/json",
        "x-goog-api-key": API_KEY,
    }

    with httpx.Client(timeout=300) as client:
        response = client.post(GEMINI_API_URL, json=payload, headers=headers)

    if response.status_code != 200:
        print(f"API Error {response.status_code}: {response.text}", file=sys.stderr)
        sys.exit(1)

    result = response.json()

    try:
        return result["candidates"][0]["content"]["parts"][0]["text"]
    except (KeyError, IndexError) as e:
        print(f"Unexpected response format: {e}", file=sys.stderr)
        print(json.dumps(result, indent=2, ensure_ascii=False), file=sys.stderr)
        sys.exit(1)


def parse_fragment_times(transcript: str) -> tuple[int, int]:
    """Extract start/end epoch times from Fragment headers in transcript."""
    dt_pattern = r"\[Fragment \d+:\s*(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2})\s*-\s*(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2})\]"
    matches = re.findall(dt_pattern, transcript)

    if matches:
        first_start = datetime.strptime(matches[0][0].strip(), "%Y-%m-%d %H:%M")
        first_start = first_start.replace(tzinfo=timezone.utc)
        last_end = datetime.strptime(matches[-1][1].strip(), "%Y-%m-%d %H:%M")
        last_end = last_end.replace(tzinfo=timezone.utc)
        return int(first_start.timestamp()), int(last_end.timestamp())

    # Fallback: use current time
    now = int(time.time())
    return now - 300, now


def build_event_json(transcript: str, user_id: str) -> dict:
    """Build event JSON matching the dataset structure."""
    start_time, end_time = parse_fragment_times(transcript)

    return {
        "meta": {
            "user_id": user_id,
            "basic_event_id": str(uuid.uuid4()),
            "basic_start_time": start_time,
            "basic_end_time": end_time,
        },
        "object": {
            "basic_transcript": transcript,
        },
    }


def main():
    parser = argparse.ArgumentParser(
        description="Extract transcript from audio and output structured event JSON"
    )
    parser.add_argument(
        "audio_file", help="Path to the audio file (MP3, WAV, M4A, etc.)"
    )
    parser.add_argument(
        "-o", "--output", help="Output JSON file path (default: print to stdout)"
    )
    parser.add_argument(
        "--user-id",
        default="79ef7f17-9d24-4a85-a6fe-de7d060bc090",
        help="User ID for the event (default: competition user ID)",
    )
    args = parser.parse_args()

    audio_path = Path(args.audio_file)
    if not audio_path.exists():
        print(f"Error: Audio file not found: {audio_path}", file=sys.stderr)
        sys.exit(1)

    print(f"Processing: {audio_path} ({audio_path.stat().st_size / 1024 / 1024:.1f} MB)")

    audio_b64, mime_type = read_audio_as_base64(str(audio_path))
    print("Transcribing audio...")
    transcript = call_gemini(TRANSCRIPTION_PROMPT, audio_b64, mime_type)
    print(f"Transcript generated ({len(transcript)} chars)")

    event = build_event_json(transcript, args.user_id)
    output_json = json.dumps(event, indent=2, ensure_ascii=False)

    if args.output:
        Path(args.output).write_text(output_json, encoding="utf-8")
        print(f"Event JSON saved to: {args.output}")
    else:
        print("\n" + output_json)


if __name__ == "__main__":
    main()
