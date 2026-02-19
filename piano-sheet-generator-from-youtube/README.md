# YouTube to Piano Sheet PDF Generator

This tool extracts piano sheet music from "video score" style YouTube videos and converts them into a high-quality, tablet-optimized PDF.

## ✨ Features

- **11:35 Precision Cropping**: Individual per-page cropping with zero extra margin for the tightest possible fit.
- **Intelligent Deduplication**: Uses SSIM (Structural Similarity Index) to eliminate duplicate frames caused by page highlights or scrolling progress bars.
- **Content-Aware Extraction**: Automatically detects page turns using video scene analysis.
- **Robust & Lightweight**: Pure shell or light Python options that work within memory constraints.

## 🛠 Prerequisites

Ensure you have the following tools installed:

- **yt-dlp**: For downloading videos.
- **ffmpeg**: For frame extraction and processing.
- **img2pdf**: For high-quality PDF generation.
- **bc**: For calculation (required for shell version).

### Installation (macOS)
```bash
brew install yt-dlp ffmpeg img2pdf
```

## 🚀 Quick Start (Recommended)

The shell script version (`main.sh`) is the most robust and stable.

```bash
# 1. Clone or download the project
# 2. Make the script executable
chmod +x main.sh

# 3. Run with a YouTube URL
./main.sh "https://www.youtube.com/watch?v=nfLsjZIolXk"
```

The output will be saved as `sheet_YYYYMMDD_HHMMSS.pdf` in the same directory.

## 🧪 For Testers

If you are helping test this tool, please check for:

1. **Page Completeness**: Ensure no pages are missing from the sequence.
2. **Duplicate Detection**: Check if there are any identical consecutive pages.
3. **Cropping Quality**: Verify that musical notes (ledger lines, dynamics, etc.) are NOT cut off at the edges.
4. **Consistency**: All pages should be tightly cropped to the sheet music area.

## 🐍 Python Version (Alternative)

If you prefer Python, use `main_zero.py` which has zero extra pip dependencies beyond the system tools above.

```bash
python3 main_zero.py "URL_HERE"
```

## 📜 How it Works

1. **Extraction**: `ffmpeg` scans the video and saves a frame only when it detects a "scene change" (a page turn).
2. **Deduplication**: The tool compares frames at the RAW level (before cropping) using SSIM (threshold 0.90) to remove redundant captures.
3. **High-Precision Crop**: `ffmpeg` detects the music area for *each page individually* and trims the black bars with zero-pixel padding for maximum visibility.
4. **Assembly**: `img2pdf` merges the high-resolution images into a single PDF without re-encoding to preserve maximum quality.

---
Developed as a lightweight, professional-grade score extraction tool.
