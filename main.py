import argparse
import os
from datetime import datetime, timedelta, timezone

import anthropic
import requests
from mutagen.mp3 import MP3
from openai import OpenAI

AUDIO_PATH = "audio/latest.mp3"
JST = timezone(timedelta(hours=9))


def require_env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(f"環境変数 {name} が設定されていません")
    return value


def generate_script() -> str:
    client = anthropic.Anthropic(api_key=require_env("ANTHROPIC_API_KEY"))
    today = datetime.now(JST).strftime("%Y年%m月%d日")

    response = client.messages.create(
        model="claude-opus-5",
        max_tokens=2000,
        output_config={"effort": "medium"},
        tools=[
            {
                "type": "web_search_20260209",
                "name": "web_search",
                "max_uses": 8,
            }
        ],
        system="あなたは日本語のニュース音声配信番組の原稿を書く放送作家です。",
        messages=[
            {
                "role": "user",
                "content": (
                    f"今日({today}, JST)の主要ニュースをweb検索ツールで調べてください。\n"
                    "条件:\n"
                    "- 総合ジャンル(政治・経済・社会・国際・スポーツなど)から、"
                    "国内外を織り交ぜて重要なニュースを5件選ぶこと\n"
                    "- 各ニュースを1〜2文程度で簡潔に要約すること\n"
                    "- 見出しの列挙ではなく、聞いて分かりやすい、自然な日本語の"
                    "話し言葉でつながった原稿にまとめること\n"
                    "- 冒頭に簡単な挨拶、末尾に簡単な締めの言葉を入れること\n"
                    "- 原稿本文のみを出力すること(見出し・Markdown記号・"
                    "番号付けなどは不要)\n"
                    "- 全体で300〜500文字程度、音声で1〜2分ほどで読み終える"
                    "長さにすること"
                ),
            }
        ],
    )

    if response.stop_reason == "refusal":
        raise RuntimeError(f"Claudeが原稿生成を拒否しました: {response.stop_details}")

    script = "".join(
        block.text for block in response.content if block.type == "text"
    ).strip()

    if not script:
        raise RuntimeError("Claudeから原稿テキストを取得できませんでした")

    return script


def synthesize_audio(script: str, out_path: str) -> None:
    client = OpenAI(api_key=require_env("OPENAI_API_KEY"))
    os.makedirs(os.path.dirname(out_path), exist_ok=True)

    with client.audio.speech.with_streaming_response.create(
        model="gpt-4o-mini-tts",
        voice="alloy",
        input=script,
        response_format="mp3",
        instructions=(
            "落ち着いた、聞き取りやすいニュースキャスターのトーンで、"
            "日本語で読んでください。"
        ),
    ) as response:
        response.stream_to_file(out_path)


def get_duration_ms(path: str) -> int:
    return int(MP3(path).info.length * 1000)


def send_line_audio(url: str, duration_ms: int) -> None:
    token = require_env("LINE_CHANNEL_ACCESS_TOKEN")
    user_id = require_env("LINE_USER_ID")

    resp = requests.post(
        "https://api.line.me/v2/bot/message/push",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        json={
            "to": user_id,
            "messages": [
                {
                    "type": "audio",
                    "originalContentUrl": url,
                    "duration": duration_ms,
                }
            ],
        },
        timeout=30,
    )
    if not resp.ok:
        print(f"LINE APIエラー ({resp.status_code}): {resp.text}")
    resp.raise_for_status()


def main() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("generate")

    send_parser = sub.add_parser("send")
    send_parser.add_argument("--url", required=True)

    args = parser.parse_args()

    if args.command == "generate":
        script = generate_script()
        print("=== 生成された原稿 ===")
        print(script)
        synthesize_audio(script, AUDIO_PATH)
        print(f"音声ファイルを生成しました: {AUDIO_PATH}")

    elif args.command == "send":
        duration_ms = get_duration_ms(AUDIO_PATH)
        send_line_audio(args.url, duration_ms)
        print(f"LINEに音声メッセージを送信しました (duration={duration_ms}ms)")


if __name__ == "__main__":
    main()
