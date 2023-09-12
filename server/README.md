# アルゴリズムのACES Platformへのデプロイ

このフォルダは実装したアルゴリズムをAPI・デモサイト化するためのACES Platformへのデプロイをサポートします。
一連のインフラ構築手順は以下の記事に記事に従って行います。

- [【マニュアル】プロジェクトアルゴリズムをAPI・デモサイト化するためのインフラ構築手順 (ACES Platform)](https://aces.kibe.la/notes/15646)
  - 参考: ACES Platform Wiki: [ACES Platform wiki](https://aces.kibe.la/notes/15537)

## フォルダ内容

全体のデプロイまでのプロセスは上記のKibela記事を参考にしてください。

- `server/infra/initial_setup`
    - 以下の手順を実行してACES Platformでサービス提供するアルゴリズムサーバのinfra環境を構築します
    - README: [推論アルゴリズムサーバのinfra環境構築](infra/initial_setup/README.md)
- `server/infra/deploy`
    - 以下の手順を実行してACES Platformでサービス提供するアルゴリズムサーバをデプロイします 
    - README: [推論アルゴリズムサーバのデプロイ](infra/deploy/README.md)
- `server/infra/config`
    - デプロイに関する設定ファイルです
