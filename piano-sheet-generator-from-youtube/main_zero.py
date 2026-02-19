import os
import sys
import subprocess
import glob
from datetime import datetime

def run_command(command, capture=False):
    if not capture:
        print(f"Running: {' '.join(command)}")
        result = subprocess.run(command, capture_output=False)
        return result.returncode == 0
    else:
        result = subprocess.run(command, capture_output=True, text=True)
        return result.stdout if result.returncode == 0 else None

def get_crop_params(img_path):
    cmd = [
        'ffmpeg', '-loop', '1', '-t', '1', '-i', img_path,
        '-vf', 'cropdetect=24:16:0',
        '-f', 'null', '-'
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    output = result.stderr
    if "crop=" in output:
        lines = output.split('\n')
        for line in reversed(lines):
            if "crop=" in line:
                return line.split("crop=")[1].split(" ")[0]
    return None

def get_ssim(img1, img2):
    cmd = [
        'ffmpeg', '-i', img1, '-i', img2,
        '-filter_complex', 'ssim',
        '-f', 'null', '-'
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    output = result.stderr
    if "All:" in output:
        try:
            parts = output.split("All:")[1].split(" ")
            return float(parts[0])
        except: return 0.0
    return 0.0

def main():
    if len(sys.argv) < 2:
        print("Usage: python3 main_zero.py <YouTube_URL>")
        sys.exit(1)
        
    url = sys.argv[1]
    video_file = 'video.mp4'
    temp_dir = 'temp_pages'
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_pdf = f"sheet_{timestamp}.pdf"
    
    if os.path.exists(temp_dir):
        for f in glob.glob(os.path.join(temp_dir, "*.jpg")):
            os.remove(f)
    else:
        os.makedirs(temp_dir)
    
    try:
        # 1. Download
        print("\n--- Step 1: Downloading video ---")
        dl_cmd = ['yt-dlp', '--no-playlist', '-f', 'mp4', '-o', video_file, url]
        if not run_command(dl_cmd): return

        # 2. Extract
        print("\n--- Step 2: Extracting pages ---")
        extract_cmd = [
            'ffmpeg', '-i', video_file,
            '-vf', "select='eq(n,0)+gt(scene,0.01)',scale=1280:-1",
            '-vsync', 'vfr',
            os.path.join(temp_dir, 'page_%03d_raw.jpg')
        ]
        if not run_command(extract_cmd): return
            
        raw_files = sorted(glob.glob(os.path.join(temp_dir, '*_raw.jpg')))
        print(f"  Extracted {len(raw_files)} raw pages.")

        # 3. Aggressive Deduplication (0.90)
        print("\n--- Step 3: Removing duplicate pages ---")
        if len(raw_files) > 1:
            kept_files = [raw_files[0]]
            for i in range(1, len(raw_files)):
                similarity = get_ssim(kept_files[-1], raw_files[i])
                print(f"  {os.path.basename(kept_files[-1])} vs {os.path.basename(raw_files[i])}: SSIM = {similarity:.4f}")
                if similarity > 0.90:
                    os.remove(raw_files[i])
                else:
                    kept_files.append(raw_files[i])
            raw_files = kept_files

        # 4. Individual High-Precision Cropping (11:35 style)
        print("\n--- Step 4: Applying 11:35 precision individual cropping ---")
        final_files = []
        for raw in raw_files:
            final_path = raw.replace('_raw.jpg', '.jpg')
            params = get_crop_params(raw)
            if params:
                print(f"  Cropping {os.path.basename(raw)} -> {params}")
                crop_cmd = ['ffmpeg', '-i', raw, '-vf', f'crop={params}', final_path]
                if run_command(crop_cmd): os.remove(raw)
                else: os.rename(raw, final_path)
            else:
                os.rename(raw, final_path)
            final_files.append(final_path)

        # 5. Generate PDF
        print(f"\n--- Step 5: Generating PDF ({len(final_files)} pages) ---")
        pdf_cmd = ['img2pdf'] + final_files + ['-o', output_pdf]
        if run_command(pdf_cmd):
            print(f"\nSuccess! '{output_pdf}' created.")

    except Exception as e:
        print(f"Error: {e}")
    finally:
        if os.path.exists(video_file): os.remove(video_file)

if __name__ == "__main__":
    main()
