DocCorNet
========

Minimal project for working with the DocCornerNet model files and training artifacts.

Quick start
-----------

1. Create and activate a Python virtual environment:

```bash
python -m venv venv
source venv/bin/activate  # or venv\Scripts\Activate.ps1 on Windows PowerShell
```

2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Open the notebook:

```bash
jupyter notebook main.ipynb
```

Files
-----

- `main.ipynb` — example notebook
- `models/` — model artifacts (Keras and TFLite)

Model Releases
--------------

A GitHub Actions workflow (`.github/workflows/release-models.yml`) automatically packages and publishes releases with:
- Individual model weights: `doccornernet_model.keras` and `doccornernet_model_fp16.tflite`
- Bundled archive: `doccornernet-models-<version>.zip`
- Training metadata: `training_history.json`
- Integrity manifest: `SHA256SUMS.txt`
- Automated release notes with metrics summary and code snippets

### Releasing a New Version

1. **Via Git Tags (Recommended)**:
   ```bash
   git tag -a v1.0.0 -m "Release v1.0.0: improved image pipeline"
   git push origin v1.0.0
   ```
2. **Via GitHub UI (Manual Dispatch)**:
   - Navigate to the **Actions** tab on GitHub.
   - Select **Release Model Version**.
   - Click **Run workflow**, optionally specifying a tag, custom title, or pre-release/draft status.

License
-------

No license specified.
