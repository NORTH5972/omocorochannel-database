# オモコロチャンネル動画データベース（非公式）

オモコロチャンネルの動画を、タイトル・出演者・主役・ジャンル・エンディングで探すためのファン制作サイトです。公式サイトではありません。

## GitHub Pagesで公開する

1. GitHubリポジトリの **Settings → Pages** を開きます。
2. **Build and deployment → Source** を **GitHub Actions** に設定します。
3. Actions タブで **Deploy static site to GitHub Pages** の実行を確認します。
4. 成功後、Pagesに表示されるURLからサイトを開きます。

このリポジトリには、mainブランチへのpush時に自動デプロイするワークフローを含みます。

## 動画データの追加

`data/videos.json` に動画オブジェクトを配列として追加します。データを変更してmainへpushすると、公開サイトに反映されます。

```json
[
  {
    "videoId": "YouTubeの動画ID",
    "title": "動画タイトル",
    "youtubeUrl": "https://www.youtube.com/watch?v=動画ID",
    "thumbnailUrl": "サムネイルURL",
    "publishedAt": "YYYY-MM-DD",
    "description": "説明",
    "performers": ["出演者A", "出演者B"],
    "protagonists": ["主役の人物"],
    "genres": ["ジャンル"],
    "endingScreen": "ending-01"
  }
]
```

- `performers`: 出演者全員
- `protagonists`: 動画の中心となる人物。複数可。主役がいなければ空配列または省略
- `genres`: ジャンル。複数可
- `endingScreen`: `data/ending-screens.json` の `id` と対応

`data/ending-screens.json` の例：

```json
[
  {
    "id": "ending-01",
    "name": "エンディング名",
    "description": "画面の特徴など"
  }
]
```

現在、データは空です。実際の動画情報を確認して登録してください。動画ファイル自体は再配布せず、動画へのリンクを使用します。サムネイルやYouTubeデータの取得・表示については、YouTubeの利用規約およびDeveloper Policiesを確認してください。
