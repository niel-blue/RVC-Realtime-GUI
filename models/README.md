# Models

モデルごとにサブフォルダーを作り、その中へRVCモデルとIndexを配置します。

```text
models/
  MyModel/
    MyModel.pth
    added_MyModel.index
```

- `.pth`があるサブフォルダーが起動時にモデル一覧へ表示されます。
- `.index`は省略できますが、その場合は`Index Rate`を`0`にしてください。
- 複数の`.pth`がある場合は、ファイル名順の先頭を使用します。
- 複数の`.index`がある場合は、`added_`で始まるファイルを優先します。
- 起動後に追加した場合は、画面の「再読み込み」を押してください。
