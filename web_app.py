import os
import subprocess
import glob
import time
import json
from datetime import datetime
from flask import Flask, render_template, request, Response, send_file, stream_with_context

app = Flask(__name__)

# Constants
TEMP_DIR = 'temp_pages'
VIDEO_FILE = 'video.mp4'

def run_script_with_logs(url):
    """Executes the generator logic while yielding real-time status updates."""
    # Step 1: Download
    yield "data: " + json.dumps({"msg": "YouTubeから動画をダウンロード中...", "type": "info"}) + "\n\n"
    dl_cmd = ['yt-dlp', '--no-playlist', '-f', 'mp4[height<=720]/best[height<=720]', '-o', VIDEO_FILE, url]
    dl_proc = subprocess.run(dl_cmd, capture_output=True, text=True)
    if dl_proc.returncode != 0:
        err_msg = dl_proc.stderr.split('\n')[0] if dl_proc.stderr else "原因不明のエラー"
        yield "data: " + json.dumps({"msg": f"ダウンロードに失敗しました: {err_msg}", "type": "error"}) + "\n\n"
        return

    # Step 2: Extract
    yield "data: " + json.dumps({"msg": "楽譜ページを抽出中...", "type": "info"}) + "\n\n"
    if os.path.exists(TEMP_DIR):
        for f in glob.glob(os.path.join(TEMP_DIR, "*.jpg")): os.remove(f)
    else: os.makedirs(TEMP_DIR)

    extract_cmd = ['ffmpeg', '-i', VIDEO_FILE, '-vf', "select='eq(n,0)+gt(scene,0.01)',scale=1280:-1", '-vsync', 'vfr', os.path.join(TEMP_DIR, 'page_%03d_raw.jpg')]
    subprocess.run(extract_cmd)
    
    raw_files = sorted(glob.glob(os.path.join(TEMP_DIR, '*_raw.jpg')))
    yield "data: " + json.dumps({"msg": f"{len(raw_files)}枚のページを検出しました。", "type": "success"}) + "\n\n"

    # Step 3: Deduplicate
    yield "data: " + json.dumps({"msg": "重複したページを削除中 (Aggressive 0.90)...", "type": "info"}) + "\n\n"
    if len(raw_files) > 1:
        kept_files = [raw_files[0]]
        for i in range(1, len(raw_files)):
            # Quick SSIM check
            cmd = ['ffmpeg', '-i', kept_files[-1], '-i', raw_files[i], '-filter_complex', 'ssim', '-f', 'null', '-']
            res = subprocess.run(cmd, capture_output=True, text=True).stderr
            ssim = 0.0
            if "All:" in res: ssim = float(res.split("All:")[1].split(" ")[0])
            
            if ssim > 0.90:
                os.remove(raw_files[i])
            else:
                kept_files.append(raw_files[i])
        raw_files = kept_files
    yield "data: " + json.dumps({"msg": f"重複を削除しました。残り: {len(raw_files)}枚", "type": "success"}) + "\n\n"

    # Step 4: Crop (11:35 Precision)
    yield "data: " + json.dumps({"msg": "11:35精度でトリミングを適用中...", "type": "info"}) + "\n\n"
    final_files = []
    for raw in raw_files:
        final_path = raw.replace('_raw.jpg', '.jpg')
        # Detect
        cmd = ['ffmpeg', '-loop', '1', '-t', '1', '-i', raw, '-vf', 'cropdetect=24:16:0', '-f', 'null', '-']
        res = subprocess.run(cmd, capture_output=True, text=True).stderr
        crop = None
        if "crop=" in res: crop = res.split("crop=")[1].split(" ")[0]
        
        if crop:
            subprocess.run(['ffmpeg', '-i', raw, '-vf', f'crop={crop}', final_path], capture_output=True)
            os.remove(raw)
        else:
            os.rename(raw, final_path)
        final_files.append(final_path)

    # Step 5: PDF
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    pdf_filename = f"sheet_{timestamp}.pdf"
    yield "data: " + json.dumps({"msg": "PDFを作成中...", "type": "info"}) + "\n\n"
    subprocess.run(['img2pdf'] + final_files + ['-o', pdf_filename])
    
    if os.path.exists(VIDEO_FILE): os.remove(VIDEO_FILE)
    
    yield "data: " + json.dumps({"msg": "完了しました！", "type": "done", "pdf": pdf_filename}) + "\n\n"

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/generate')
def generate():
    url = request.args.get('url')
    if not url: return Response("Missing URL", status=400)
    return Response(stream_with_context(run_script_with_logs(url)), mimetype='text/event-stream')

@app.route('/download/<filename>')
def download(filename):
    if os.path.exists(filename):
        return send_file(filename, as_attachment=True)
    return "File not found", 404

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
