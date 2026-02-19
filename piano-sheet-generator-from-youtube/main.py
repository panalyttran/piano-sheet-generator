import os
import sys
import cv2
import yt_dlp
import img2pdf
from PIL import Image
from utils import is_similar, crop_black_bars

def download_video(url, output_path='video.mp4'):
    ydl_opts = {
        'format': 'bestvideo[height<=720]+bestaudio/best[height<=720]',
        'outtmpl': output_path,
        'merge_output_format': 'mp4',
        'noplaylist': True,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])
    return output_path

def extract_pages(video_path, output_folder='temp_pages'):
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)
        
    cap = cv2.VideoCapture(video_path)
    fps = cap.get(cv2.CAP_PROP_FPS)
    
    last_frame = None
    page_count = 0
    saved_paths = []
    
    # Check every 1 second to find page changes
    frame_interval = int(fps) 
    
    frame_idx = 0
    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break
            
        if frame_idx % frame_interval == 0:
            if last_frame is None or not is_similar(last_frame, frame):
                # New page detected!
                page_count += 1
                img_path = os.path.join(output_folder, f"page_{page_count:03d}.jpg")
                
                # Convert to PIL for cropping and saving
                rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                pil_img = Image.fromarray(rgb_frame)
                cropped_img = crop_black_bars(pil_img)
                cropped_img.save(img_path, quality=95)
                
                saved_paths.append(img_path)
                print(f"Captured page {page_count} at {frame_idx/fps:.2f}s")
                last_frame = frame.copy()
        
        frame_idx += 1
        
    cap.release()
    return saved_paths

def create_pdf(image_paths, output_pdf='output.pdf'):
    with open(output_pdf, "wb") as f:
        f.write(img2pdf.convert(image_paths))
    print(f"PDF created: {output_pdf}")

def main():
    if len(sys.argv) < 2:
        print("Usage: python main.py <YouTube_URL>")
        sys.exit(1)
        
    url = sys.argv[1]
    video_file = 'video.mp4'
    temp_dir = 'temp_pages'
    
    try:
        print("Downloading video...")
        download_video(url, video_file)
        
        print("Extracting pages...")
        image_paths = extract_pages(video_file, temp_dir)
        
        if not image_paths:
            print("No pages were extracted.")
            return
            
        print(f"Generating PDF from {len(image_paths)} pages...")
        create_pdf(image_paths)
        
        print("Done!")
        
    except Exception as e:
        print(f"Error: {e}")
    finally:
        # Cleanup
        if os.path.exists(video_file):
            os.remove(video_file)
        # We keep the temp folder for user review, but typically could cleanup:
        # for f in os.listdir(temp_dir): os.remove(os.path.join(temp_dir, f))

if __name__ == "__main__":
    main()
