import os
import sys
import subprocess
from PIL import Image
import img2pdf

def run_command(command):
    print(f"Running: {' '.join(command)}")
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"Error: {result.stderr}")
    return result.returncode == 0

def download_video(url, output_path='video.mp4'):
    command = [
        'yt-dlp', 
        '--no-playlist',
        '-f', 'bestvideo[height<=720][ext=mp4]/best[height<=720][ext=mp4]', 
        '-o', output_path, 
        url
    ]
    return run_command(command)

def extract_pages(video_path, output_folder='temp_pages'):
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)
    
    # Use ffmpeg to detect scene changes and save frames
    # eq(n,0) for first frame, scene=0.01 is more sensitive
    command = [
        'ffmpeg', '-i', video_path,
        '-vf', "select='eq(n,0)+gt(scene,0.01)',scale=1280:-1",
        '-vsync', 'vfr',
        os.path.join(output_folder, 'page_%03d.jpg')
    ]
    return run_command(command)

def crop_and_finalize(output_folder):
    files = sorted([f for f in os.listdir(output_folder) if f.endswith('.jpg')])
    image_paths = []
    
    print(f"Processing {len(files)} extracted frames...")
    for f in files:
        path = os.path.join(output_folder, f)
        img = Image.open(path)
        
        # Simple auto-crop using bounding box
        # This is memory-light compared to OpenCV
        bg = Image.new(img.mode, img.size, img.getpixel((0,0)))
        diff = ImageChops.difference(img, bg)
        diff = ImageChops.add(diff, diff, 2.0, -100)
        bbox = diff.getbbox()
        if bbox:
            img = img.crop(bbox)
        
        # Save high quality
        img.save(path, "JPEG", quality=95)
        image_paths.append(path)
        
    return image_paths

def main():
    if len(sys.argv) < 2:
        print("Usage: python3 main_light.py <YouTube_URL>")
        sys.exit(1)
        
    url = sys.argv[1]
    video_file = 'video.mp4'
    temp_dir = 'temp_pages'
    
    try:
        print("--- Step 1: Downloading video ---")
        if not download_video(url, video_file):
            print("Download failed.")
            return

        print("\n--- Step 2: Extracting pages using ffmpeg ---")
        if not extract_pages(video_file, temp_dir):
            print("Extraction failed.")
            return
            
        files = [os.path.join(temp_dir, f) for f in os.listdir(temp_dir) if f.endswith('.jpg')]
        if not files:
            print("No pages detected. Try lowering the scene threshold in the script.")
            return
            
        print(f"\n--- Step 3: Generating PDF from {len(files)} pages ---")
        with open("output.pdf", "wb") as f:
            f.write(img2pdf.convert(sorted(files)))
        
        print("\nSuccess! Generated output.pdf")
        
    except Exception as e:
        print(f"Error: {e}")
    finally:
        if os.path.exists(video_file):
            os.remove(video_file)

if __name__ == "__main__":
    # Need ImageChops for cropping
    from PIL import ImageChops
    main()
