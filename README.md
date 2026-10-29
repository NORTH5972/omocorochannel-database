# オモコロチャンネル動画データベース（非公式）

オモコロチャンネルの動画を、タイトル・出演者・主役・ジャンル・エンディングで探すためのファン制作サイトです。公式サイトではありません。

## 公開サイト

https://north5972.github.io/omocorochannel-database/

## 現在のデータ

- YouTubeの公開動画一覧から取得した動画メタデータを登録しています（初回収集では1,339件）。
- タイトル、公開日、動画URL、サムネイルURLを自動取得します。
- 出演者・主役・ジャンル・エンディングは自動推測せず、確認済みデータのみ登録する方針です。未確認の分類項目は空欄です。
- 自動収集は毎日実行し、新しい動画を追加します。過去に削除・非公開になった動画や、YouTube側で一覧に出ない動画は含まれない場合があります。

## データの編集

動画データは `data/videos.json`、エンディング情報は `data/ending-screens.json` にあります。

動画オブジェクトの主な項目：

```json
{
  "id": "YouTubeの動画ID",
  "title": "動画タイトル",
  "url": "https://www.youtube.com/watch?v=動画ID",
  "thumbnailUrl": "https://i.ytimg.com/vi/動画ID/hqdefault.jpg",
  "publishedAt": "YYYY-MM-DD",
  "description": "",
  "performers": [],
  "protagonists": [],
  "genres": [],
  "endingScreen": "",
  "reviewStatus": "タグ未確認"
}
```

- `performers`: 動画に出演している人物全員
- `protagonists`: 動画の中心となる人物。複数可。主役がいない場合は空配列
- `genres`: 動画のジャンル。複数可
- `endingScreen`: `data/ending-screens.json` の `id` と対応
- `reviewStatus`: 分類情報の確認状態

## 自動収集

`.github/workflows/collect-videos.yml` が毎日、YouTubeチャンネルの公開動画一覧を取得します。動画本編はダウンロードせず、タイトルやURLなどのメタデータのみを記録します。

## 注意

動画本編・サムネイル等の権利は各権利者に帰属します。YouTubeのデータ取得・表示は、YouTubeの利用規約とDeveloper Policiesを確認したうえで運用してください。


## 管理者向け編集画面（準備中）

公開日・出演者を管理画面から直接編集するためのCloudflare Worker構成を `worker/` に追加しました。GitHub AppとCloudflare Worker/KVの初期設定が必要です。手順と必要な設定値は [worker/README.md](worker/README.md) を参照してください。秘密情報はリポジトリに登録しないでください。
