# news-audio-line

毎朝 8:00 (JST) に GitHub Actions で自動実行する、ニュース音声配信システム。

## 処理内容

1. Claude (`claude-opus-5`) が Web 検索ツールを使って、その日の主要ニュース5件
   (総合ジャンル、国内外) を調べ、音声原稿にまとめる
2. OpenAI TTS (`gpt-4o-mini-tts`) で原稿を mp3 に変換
3. 生成した mp3 をリポジトリの `audio/latest.mp3` にコミット・push し、
   jsDelivr の CDN URL 経由で LINE から取得可能にする
4. LINE Messaging API (push message) で、自分の LINE に音声メッセージとして送信

## 必要な準備

### 1. リポジトリを Public にする

LINE の音声メッセージは `originContentUrl` に指定した URL を LINE のサーバーが
直接フェッチする仕組みのため、mp3 を置くリポジトリは **Public** である必要が
あります (Private だと LINE 側から取得できません)。

### 2. GitHub Secrets の設定

このリポジトリの Settings → Secrets and variables → Actions で、以下を登録する:

| Secret名 | 内容 |
|---|---|
| `ANTHROPIC_API_KEY` | Anthropic API キー |
| `OPENAI_API_KEY` | OpenAI API キー |
| `LINE_CHANNEL_ACCESS_TOKEN` | LINE Messaging API のチャネルアクセストークン |
| `LINE_USER_ID` | 送信先 (自分) の LINE ユーザーID |

### 3. push する

```
git init
git add .
git commit -m "Initial commit"
git branch -M main
git remote add origin <あなたのリポジトリURL>
git push -u origin main
```

## 動作確認

Actions タブから `Daily News Audio to LINE` ワークフローを選び、
「Run workflow」で手動実行して動作確認できる (`workflow_dispatch` 対応済み)。

## カスタマイズ

- 実行時刻: `.github/workflows/daily-news.yml` の `cron` を変更
  (UTC 指定。JST = UTC+9)
- 声質: `main.py` の `synthesize_audio()` 内の `voice=` を変更
  (`alloy` / `echo` / `fable` / `onyx` / `nova` / `shimmer` など)
- 原稿の長さ・トーン: `main.py` の `generate_script()` 内のプロンプトを変更
- ニュースの選び方: 同プロンプトの条件部分を変更 (ジャンルを絞る、件数を
  変えるなど)

## 注意点

- 毎日 `audio/latest.mp3` を上書き・コミットするため、リポジトリの履歴に
  日々の mp3 が積み重なる。気になる場合は定期的に履歴を squash するか、
  Git LFS の導入を検討する
- Claude の Web 検索結果の品質はニュースサイトの検索結果次第のため、
  内容の正確性は都度軽く確認することを推奨
