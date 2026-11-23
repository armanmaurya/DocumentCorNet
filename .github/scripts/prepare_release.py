#!/usr/bin/env python3
"""
prepare_release.py
Prepares model release assets, builds a bundled zip archive, computes SHA-256 checksums,
and generates a rich markdown release description.
"""

import argparse
import hashlib
import json
import os
import shutil
import sys
import zipfile
from pathlib import Path


def format_size(num_bytes: int) -> str:
    """Format file size in human-readable units."""
    for unit in ["B", "KB", "MB", "GB"]:
        if num_bytes < 1024.0:
            return f"{num_bytes:.2f} {unit}" if unit != "B" else f"{num_bytes} B"
        num_bytes /= 1024.0
    return f"{num_bytes:.2f} TB"


def sha256_file(filepath: Path) -> str:
    """Compute SHA-256 checksum of a file."""
    hasher = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest()


def extract_training_metrics(history_path: Path) -> str:
    """Extract key metrics from training_history.json if present."""
    if not history_path.exists():
        return ""

    try:
        with open(history_path, "r", encoding="utf-8") as f:
            history = json.load(f)
    except Exception as e:
        print(f"Warning: Failed to parse {history_path}: {e}", file=sys.stderr)
        return ""

    if not isinstance(history, dict) or not history:
        return ""

    epochs = 0
    metric_rows = []

    metrics_spec = [
        ("loss", "Training Loss", "min"),
        ("val_loss", "Validation Loss", "min"),
        ("presence_acc", "Presence Accuracy", "max"),
        ("val_presence_acc", "Val Presence Accuracy", "max"),
        ("presence_auc", "Presence AUC", "max"),
        ("val_presence_auc", "Val Presence AUC", "max"),
        ("heatmap_mae", "Heatmap MAE", "min"),
        ("val_heatmap_mae", "Val Heatmap MAE", "min"),
    ]

    for key, label, direction in metrics_spec:
        if key in history and isinstance(history[key], list) and len(history[key]) > 0:
            values = history[key]
            epochs = max(epochs, len(values))
            final_val = values[-1]
            best_val = min(values) if direction == "min" else max(values)
            metric_rows.append(
                f"| **{label}** | {final_val:.6f} | {best_val:.6f} ({direction}) |"
            )

    if not metric_rows:
        return ""

    section = [
        "### 📊 Training Summary",
        f"- **Total Trained Epochs**: {epochs}",
        "",
        "| Metric | Final Epoch Value | Best Value |",
        "| :--- | :--- | :--- |",
    ]
    section.extend(metric_rows)
    section.append("")
    return "\n".join(section)


def main():
    parser = argparse.ArgumentParser(description="Prepare model release assets and summary.")
    parser.add_argument("--tag", required=True, help="Release version tag (e.g. v1.0.0)")
    parser.add_argument(
        "--models-dir",
        default="models",
        type=Path,
        help="Path to models directory (default: models)",
    )
    parser.add_argument(
        "--output-dir",
        default="release_assets",
        type=Path,
        help="Output staging directory for release files (default: release_assets)",
    )
    parser.add_argument(
        "--body-output",
        default="release_body.md",
        type=Path,
        help="Output markdown file for release notes (default: release_body.md)",
    )

    args = parser.parse_args()

    models_dir = args.models_dir.resolve()
    output_dir = args.output_dir.resolve()
    body_output = args.body_output.resolve()
    tag = args.tag

    if not models_dir.exists() or not models_dir.is_dir():
        print(f"Error: Models directory not found at {models_dir}", file=sys.stderr)
        sys.exit(1)

    # 1. Clean and recreate output directory
    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # 2. Identify model files to include
    candidate_files = [f for f in sorted(models_dir.iterdir()) if f.is_file()]
    if not candidate_files:
        print(f"Error: No files found in {models_dir}", file=sys.stderr)
        sys.exit(1)

    print(f"Found {len(candidate_files)} model files in {models_dir}:")
    for f in candidate_files:
        print(f" - {f.name} ({format_size(f.stat().st_size)})")

    # 3. Copy individual files to output_dir
    copied_files = []
    for f in candidate_files:
        dest = output_dir / f.name
        shutil.copy2(f, dest)
        copied_files.append(dest)

    # 4. Create bundled zip archive
    zip_name = f"doccornernet-models-{tag}.zip"
    zip_path = output_dir / zip_name
    print(f"Creating bundled archive: {zip_path.name}")
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
        for f in candidate_files:
            zipf.write(f, arcname=f.name)

    all_release_files = copied_files + [zip_path]

    # 5. Compute SHA-256 checksums and write SHA256SUMS.txt
    checksums = {}
    checksum_lines = []
    for f in sorted(all_release_files, key=lambda x: x.name):
        h = sha256_file(f)
        checksums[f.name] = h
        checksum_lines.append(f"{h}  {f.name}")

    checksum_file = output_dir / "SHA256SUMS.txt"
    with open(checksum_file, "w", encoding="utf-8") as f:
        f.write("\n".join(checksum_lines) + "\n")

    # 6. Generate Release Body Markdown
    metrics_section = extract_training_metrics(models_dir / "training_history.json")

    assets_rows = []
    for f in sorted(all_release_files, key=lambda x: x.name):
        size_str = format_size(f.stat().st_size)
        h = checksums[f.name]
        assets_rows.append(f"| `{f.name}` | {size_str} | `{h}` |")
    checksum_file_size = format_size(checksum_file.stat().st_size)
    assets_rows.append(f"| `SHA256SUMS.txt` | {checksum_file_size} | *Checksum manifest file* |")

    body_content = f"""## 🏷️ Release {tag}

Model checkpoint and deployment artifacts for **DocCornerNet** ({tag}).

{metrics_section}
### 📦 Assets & Verification

| Asset | Size | SHA-256 Checksum |
| :--- | :--- | :--- |
{chr(10).join(assets_rows)}

### 🔍 Checksum Verification
You can verify file integrity using the provided manifest:
```bash
sha256sum -c SHA256SUMS.txt
```

### 💻 Quick Usage

#### Load Keras Model (.keras)
```python
import tensorflow as tf

# Load the trained model
model = tf.keras.models.load_model("doccornernet_model.keras")
predictions = model.predict(image_batch)
```

#### Run TFLite Inference (.tflite)
```python
import numpy as np
import tensorflow as tf

# Initialize TFLite interpreter
interpreter = tf.lite.Interpreter(model_path="doccornernet_model_fp16.tflite")
interpreter.allocate_tensors()

input_details = interpreter.get_input_details()
output_details = interpreter.get_output_details()

# Set input and invoke
interpreter.set_tensor(input_details[0]['index'], input_data)
interpreter.invoke()
output_data = interpreter.get_tensor(output_details[0]['index'])
```
"""

    with open(body_output, "w", encoding="utf-8") as f:
        f.write(body_content)

    print(f"Generated release notes at {body_output}")
    print("Release preparation complete!")


if __name__ == "__main__":
    main()
