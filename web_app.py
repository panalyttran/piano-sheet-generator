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
    
    # Precise download with robust fallback
    dl_cmd = [
        'yt-dlp', '--no-playlist', 
        '-f', 'best[height<=720]/best', 
        '--newline', '--progress', '--no-check-certificates', '--geo-bypass',
        '--extractor-args', 'youtube:player-client=android,web,tv,tv_embedded',
        '-o', VIDEO_FILE, url
    ]
    
    # 1. Check JS runtime (for n-challenge)
    try:
        node_v = subprocess.run(['node', '-v'], capture_output=True, text=True).stdout.strip()
        yield "data: " + json.dumps({"msg": f"システム状況: Node.js {node_v} 検出", "type": "info"}) + "\n\n"
    except:
        yield "data: " + json.dumps({"msg": "警告: JavaScript環境(Node.js)が見つかりません。ダウンロードが制限される可能性があります。", "type": "info"}) + "\n\n"

    # 2. Flexible cookie detection
    cookie_files = glob.glob('*cookies.txt')
    if cookie_files:
        cookie_file = cookie_files[0]
        dl_cmd.extend(['--cookies', cookie_file])
        yield "data: " + json.dumps({"msg": f"Cookieファイルを検出しました: {cookie_file}", "type": "info"}) + "\n\n"
        # Validate cookie format briefly
        with open(cookie_file, 'r') as f:
            head = f.read(20)
            if 'netscape' in head.lower() or '#' in head:
                yield "data: " + json.dumps({"msg": "Cookie形式を確認しました(Netscape形式)。", "type": "info"}) + "\n\n"
            else:
                yield "data: " + json.dumps({"msg": "警告: Cookieの形式が正しくない可能性があります(Netscape形式を推奨)。", "type": "info"}) + "\n\n"
    else:
        yield "data: " + json.dumps({"msg": "Cookieファイルが見つかりません。匿名モードで実行します。", "type": "info"}) + "\n\n"
    
    last_lines = []
    process = subprocess.Popen(dl_cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    for line in process.stdout:
        line = line.strip()
        if not line: continue
        last_lines.append(line)
        if len(last_lines) > 5: last_lines.pop(0) # Keep last 5 lines for error context

        if '[download]' in line and '%' in line:
            # Try to extract percentage
            try:
                percent = line.split('%')[0].split()[-1]
                yield "data: " + json.dumps({"msg": f"ダウンロード中... {percent}%", "type": "info"}) + "\n\n"
            except: pass
    
    process.wait()
    if process.returncode != 0:
        err_context = " ".join(last_lines)
        yield "data: " + json.dumps({"msg": f"ダウンロードに失敗しました: {err_context}", "type": "error"}) + "\n\n"
        return

    # Step 2: Extract
    yield "data: " + json.dumps({"msg": "楽譜ページを抽出中...", "type": "info"}) + "\n\n"
    if os.path.exists(TEMP_DIR):
        for f in glob.glob(os.path.join(TEMP_DIR, "*.jpg")): os.remove(f)
    else: os.makedirs(TEMP_DIR)

    # Use n=120 to skip potential title cards/black frames at start (~4-5s)
    extract_cmd = ['ffmpeg', '-i', VIDEO_FILE, '-vf', "select='eq(n,120)+gt(scene,0.02)',scale=1280:-1", '-vsync', 'vfr', os.path.join(TEMP_DIR, 'page_%03d_raw.jpg')]
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
