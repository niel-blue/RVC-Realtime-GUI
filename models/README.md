# Models

Create one folder for each RVC model under `models/`. The folder name is shown
in the application as the model name.

```text
models/
  MyModel/
    MyModel.pth
    added_MyModel.index
    preview.png        # optional
```

- Put the RVC model file (`.pth`) in the model folder.
- Put its retrieval index (`.index`) in the same folder. An `added_*.index`
  file is recommended.
- If the folder contains a PNG, JPG, or JPEG image, the application uses it as
  the model preview automatically. The file name does not matter.
- The folder name, for example `MyModel`, is displayed as the model name in the
  model list and preview panel.

After copying a model folder, use **Reload** in the application to scan it.
