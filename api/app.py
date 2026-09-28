from flask import Flask, jsonify, request
app = Flask(__name__)
app.json.ensure_ascii = False
app.config['MAX_CONTENT_LENGTH'] = 64 * 1024

@app.get('/api/health')
def health():
    return jsonify(status='ok', student_id='2024030', name='박용빈')

@app.errorhandler(413)
def too_large(error):
    return jsonify(error='입력 내용이 너무 큽니다.'), 413


from io import BytesIO
from pathlib import Path
import os
import sqlite3
from flask import send_file

DATA_DIR = Path(os.environ.get('DATA_DIR', '/data'))
DATA_DIR.mkdir(parents=True, exist_ok=True)
DB = DATA_DIR / 'views.db'
with sqlite3.connect(DB) as db:
    db.execute('CREATE TABLE IF NOT EXISTS page_views (id INTEGER PRIMARY KEY CHECK(id=1), count INTEGER NOT NULL)')
    db.execute('INSERT OR IGNORE INTO page_views VALUES (1, 0)')

@app.route('/api/views', methods=['GET', 'POST'])
def views():
    # UPDATE를 DB에서 수행하여 동시 요청으로 증가분이 사라지는 것을 막습니다.
    with sqlite3.connect(DB, timeout=10) as db:
        if request.method == 'POST':
            db.execute('UPDATE page_views SET count=count+1 WHERE id=1')
        count = db.execute('SELECT count FROM page_views WHERE id=1').fetchone()[0]
    return jsonify(views=count)

def bullets(value):
    # 화면 목록(li)은 innerText에서 줄 단위로 오므로 Markdown 목록으로 바꿉니다.
    lines = [line.strip() for line in value.splitlines() if line.strip()]
    return '\n'.join(line if line.startswith('- ') else f'- {line}' for line in lines)

@app.post('/api/download')
def download():
    data = request.get_json(silent=True)
    fields = ['title', 'summary', 'features', 'technology']
    if not isinstance(data, dict) or any(not isinstance(data.get(k), str) or not data[k].strip() for k in fields):
        return jsonify(error='프로젝트명·소개·주요 기능·사용 기술을 모두 작성하세요.'), 400
    optional = {k: data.get(k) if isinstance(data.get(k), str) else '' for k in ['tagline', 'details']}
    if any(len(v) > 5000 for v in [*(data[k] for k in fields), *optional.values()]):
        return jsonify(error='각 항목은 5,000자 이내로 작성하세요.'), 400
    text = f"# {data['title'].strip()}\n\n"
    if optional['tagline'].strip():
        text += f"> {optional['tagline'].strip()}\n\n"
    text += (f"## 프로젝트 소개\n{data['summary'].strip()}\n\n"
             f"## 주요 기능\n{bullets(data['features'])}\n\n"
             f"## 사용 기술\n{bullets(data['technology'])}\n")
    if optional['details'].strip():
        text += f"\n## 팀 소개 · 프로젝트 정보\n{bullets(optional['details'])}\n"
    return send_file(BytesIO(text.encode('utf-8')), as_attachment=True,
                     download_name='project-intro.md', mimetype='text/markdown; charset=utf-8')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
