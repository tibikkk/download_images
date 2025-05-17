import os
import shutil
import threading
from flask import (
    Flask, render_template, request,
    send_file, jsonify, url_for
)
from crawler import crawl_and_download, CrawlError

app = Flask(__name__)
app.secret_key = os.environ.get('FLASK_SECRET', 'sigmaboy')

BASE_DIR = os.path.dirname(__file__)
WORKDIR = os.path.join(BASE_DIR, 'downloads')
IMG_DIR = os.path.join(WORKDIR, 'imgs')
ZIP_BASE = os.path.join(WORKDIR, 'result')

def ensure_dirs():
    for path in (WORKDIR, IMG_DIR):
        os.makedirs(path, exist_ok=True)
    # Clean leftover archives
    for ext in ('', '.zip'):
        try:
            os.remove(ZIP_BASE + ext)
        except OSError:
            pass

ensure_dirs()

download_ready = False

@app.route('/', methods=['GET'])
def index():
    return render_template('index.html')

@app.route('/', methods=['POST'])
def start_crawl():
    global download_ready
    download_ready = False
    data = request.get_json() or {}
    raw_url = data.get('url', '').strip()
    if not raw_url:
        return jsonify(error='Please enter a URL or domain.'), 400
    if not raw_url.startswith(('http://', 'https://')):
        raw_url = 'http://' + raw_url
    # Reset workspace
    shutil.rmtree(IMG_DIR, ignore_errors=True)
    os.makedirs(IMG_DIR, exist_ok=True)
    ensure_dirs()

    def worker():
        global download_ready
        try:
            crawl_and_download(raw_url, output_dir=IMG_DIR)
            shutil.make_archive(ZIP_BASE, 'zip', root_dir=IMG_DIR)
        except CrawlError as e:
            # log or ignore
            pass
        finally:
            download_ready = True

    threading.Thread(target=worker, daemon=True).start()
    return jsonify(download_url=url_for('download'))

@app.route('/status')
def status():
    return jsonify(ready=download_ready)

@app.route('/download', methods=['GET', 'DELETE'])
def download():
    archive = ZIP_BASE + '.zip'
    if request.method == 'DELETE':
        if os.path.exists(archive):
            os.remove(archive)
        return ('', 204)
    if not os.path.exists(archive):
        return jsonify(error='Archive not ready'), 404
    return send_file(
        archive,
        as_attachment=True,
        download_name='images.zip',
        mimetype='application/zip'
    )

if __name__ == '__main__':
    app.run(debug=True)