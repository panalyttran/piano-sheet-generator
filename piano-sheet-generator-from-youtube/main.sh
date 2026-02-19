#!/bin/bash

# YouTube to Piano Sheet PDF Generator (11:35 Precision Successor)
# Requirements: yt-dlp, ffmpeg, img2pdf, bc

URL=$1
VIDEO_FILE="video.mp4"
TEMP_DIR="temp_pages"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
OUTPUT_PDF="sheet_${TIMESTAMP}.pdf"

if [ -z "$URL" ]; then
    echo "Usage: ./main.sh <YouTube_URL>"
    exit 1
fi

# 1. Clean up old files
echo "--- Cleaning up ---"
rm -rf "$TEMP_DIR" "$VIDEO_FILE"
mkdir -p "$TEMP_DIR"

# 2. Download video
echo "--- Step 1: Downloading video ---"
yt-dlp --no-playlist -f "mp4[height<=720]/best[height<=720]" -o "$VIDEO_FILE" "$URL"

if [ $? -ne 0 ]; then
    echo "Download failed."
    exit 1
fi

# 3. Extract frames
echo "--- Step 2: Extracting pages ---"
ffmpeg -i "$VIDEO_FILE" -vf "select='eq(n,0)+gt(scene,0.01)',scale=1280:-1" -vsync vfr "$TEMP_DIR/page_%03d_raw.jpg"

RAW_COUNT=$(find "$TEMP_DIR" -name "*_raw.jpg" | wc -l | tr -d ' ')
echo "  Extracted $RAW_COUNT raw pages."

# 4. Aggressive Deduplication (Threshold 0.90)
echo "--- Step 3: Removing duplicate pages (Aggressive 0.90) ---"
RAW_FILES=($(find "$TEMP_DIR" -name "*_raw.jpg" | sort))
PREV_FILE=""
DEL_COUNT=0

for FILE in "${RAW_FILES[@]}"; do
    if [ -z "$PREV_FILE" ]; then
        PREV_FILE="$FILE"
        continue
    fi

    SSIM_SCORE=$(ffmpeg -i "$PREV_FILE" -i "$FILE" -filter_complex "ssim" -f null - 2>&1 | grep "All:" | sed -e 's/.*All:\([0-9.]*\).*/\1/')
    echo "  $(basename "$PREV_FILE") vs $(basename "$FILE"): SSIM = $SSIM_SCORE"

    # Threshold 0.90 kills duplicates caused by moving highlights
    IS_DUPLICATE=$(echo "$SSIM_SCORE > 0.90" | bc -l 2>/dev/null || echo "0")
    if [ "$IS_DUPLICATE" -eq 1 ]; then
        echo "    -> Deleting duplicate"
        rm "$FILE"
        DEL_COUNT=$((DEL_COUNT + 1))
    else
        PREV_FILE="$FILE"
    fi
done
echo "  Remaining: $((RAW_COUNT - DEL_COUNT))"

# 5. Individual High-Precision Cropping (11:35 Style Re-implementation)
echo "--- Step 4: Applying 11:35-style individual precise cropping ---"
REMAIN_RAWS=($(find "$TEMP_DIR" -name "*_raw.jpg" | sort))

for RAW in "${REMAIN_RAWS[@]}"; do
    FINAL="${RAW%_raw.jpg}.jpg"
    
    # 11:35 logic: individual detect with ZERO extra padding
    CROP=$(ffmpeg -loop 1 -t 1 -i "$RAW" -vf "cropdetect=24:16:0" -f null - 2>&1 | grep "crop=" | tail -1 | sed -e 's/.*crop=\([0-9:]*\).*/\1/')
    
    if [ ! -z "$CROP" ]; then
        # Just use the detected parameters as-is for maximum tightness
        echo "  Cropping $(basename "$RAW") -> $CROP"
        ffmpeg -i "$RAW" -vf "crop=$CROP" "$FINAL" > /dev/null 2>&1
        if [ $? -eq 0 ]; then rm "$RAW"; else mv "$RAW" "$FINAL"; fi
    else
        mv "$RAW" "$FINAL"
    fi
done

# 6. Generate PDF
echo "--- Step 5: Generating PDF ---"
JPG_FILES=($(find "$TEMP_DIR" -name "*.jpg" | sort))
if command -v img2pdf >/dev/null 2>&1; then
    img2pdf "${JPG_FILES[@]}" -o "$OUTPUT_PDF"
    echo "--- Success! ---"
    echo "Generated: $OUTPUT_PDF (${#JPG_FILES[@]} pages)"
    rm -f "$VIDEO_FILE"
else
    echo "img2pdf not found."
    exit 1
fi
