from flask import Flask, render_template, request, send_from_directory
from yt_dlp import YoutubeDL
import os, tempfile, browser_cookie3

app = Flask(__name__)
DOWNLOAD_FOLDER = 'downloads'
os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)

def get_cookies_file(uploaded_file=None):
    if uploaded_file:
        temp_path = tempfile.NamedTemporaryFile(delete=False, suffix=".txt").name
        uploaded_file.save(temp_path)
        return temp_path
    try:
        cj = browser_cookie3.chrome(domain_name='youtube.com')
        cookie_file = tempfile.NamedTemporaryFile(delete=False, suffix=".txt")
        with open(cookie_file.name, 'w') as f:
            for cookie in cj:
                f.write(f"{cookie.domain}\t{cookie.path}\t{str(cookie.secure).upper()}\t{cookie.expires}\t{cookie.name}\t{cookie.value}\n")
        return cookie_file.name
    except:
        return None

def fetch_formats(url, cookie_file=None):
    ydl_opts = {'cookiefile': cookie_file} if cookie_file else {}
    with YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
        res_list = []
        for f in info.get('formats', []):
            if f.get('vcodec') != 'none':
                label = f"{f.get('format_id')} - {f.get('height','unknown')}p ({f.get('ext','')})"
                label += " [video-only]" if f.get('acodec')=='none' else " [video+audio]"
                if label not in res_list:
                    res_list.append(label)
        res_list.sort(key=lambda x: int(x.split(' - ')[1].replace('p','')) if 'p' in x else 0, reverse=True)
        return res_list

@app.route('/', methods=['GET','POST'])
def index():
    message = ''
    formats = []
    last_url = ''
    if request.method=='POST':
        action = request.form.get('action')
        url = request.form.get('video_url') or request.form.get('playlist_url')
        last_url = url
        cookie_file_to_use = get_cookies_file(request.files.get('cookie_file'))

        if not url:
            message = "Please enter a URL"
        elif action=='fetch_formats':
            try: formats = fetch_formats(url, cookie_file_to_use)
            except Exception as e: message=str(e)
        elif action=='download_video':
            try:
                format_code = request.form.get('format_code')
                if not format_code: message="Please select a format"
                else:
                    format_id = format_code.split(' - ')[0]
                    opts = {'outtmpl': os.path.join(DOWNLOAD_FOLDER, '%(title)s.%(ext)s'),
                            'format': format_id + '+bestaudio/best' if '[video-only]' in format_code else format_id}
                    if cookie_file_to_use: opts['cookiefile']=cookie_file_to_use
                    with YoutubeDL(opts) as ydl:
                        info=ydl.extract_info(url, download=True)
                        filename=ydl.prepare_filename(info)
                    return send_from_directory(DOWNLOAD_FOLDER, os.path.basename(filename), as_attachment=True)
            except Exception as e: message=str(e)
        elif action=='download_playlist':
            try:
                opts = {'outtmpl': os.path.join(DOWNLOAD_FOLDER, '%(playlist_index)s - %(title)s.%(ext)s'),
                        'ignoreerrors': True}
                if cookie_file_to_use: opts['cookiefile']=cookie_file_to_use
                with YoutubeDL(opts) as ydl: ydl.download([url])
                message="Playlist download completed!"
            except Exception as e: message=str(e)
    return render_template('index.html', message=message, formats=formats, last_url=last_url)

if __name__=='__main__':
    app.run(debug=True)
