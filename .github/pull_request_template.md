## 概要
このPRの目的と何を実装したかの概要を記入してください。

e.g. 
> QuestionnaireFormatterのis_answer_ids_validを満たす条件が厳しすぎるため、それを緩めた。
> またサーバとの繋ぎ込みの処理をスムーズにするため、性別と年代についてもQuestionnaireFormatter側で処理するように変更した。

### projectのwiki
[【wiki】project wiki@YYYYMMDD]()

### PRの関連リンク
- 検証設計: [【検討・整理】project 検証設計@YYYYMMDD]()
- 検証記事: [【検討・整理】project 検証@YYYYMMDD]()
- Trello カード: [Trello]()


## 主な変更点
変更した箇所を具体的に箇条書きで記入してください。

e.g.
> - aces-vision側のモデルをs3://project-zeus-suggest-glass/root/datadrive/にアップロードした。download_acesvision_model.pyを廃止して、README.mdに記載した通り直接aws s3 cpを行う想定。
> - 「近い形の玉型も得点に含める処理」「メガネ印象の距離の計算」がunittest通らなかったため修正。
> - 古いカラム名を使用していた箇所をアップデート。

## TODO
基本的に全て満たしていることを確認してからPRを提出してください。ただし、これらの確認が不要なPRもあると思うのでその際はその旨を記入してください。
- [ ] flake8
- [ ] 動作確認
- [ ] s3へのアップロード (s3のディレクトリ構造は docs/README.md を参照してください。)

プロジェクトがコードの納品・API提供を含む場合、unittestを作成し納品対象外の不要ファイルを削除してください。
- [ ] unittest
- [ ] 納品対象外のコード削除(e.g. server/, .github/, ...)

## 備考
自由記述欄
