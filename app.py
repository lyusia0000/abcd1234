import os
import pandas as pd
import io
import sqlite3
from flask import Flask, render_template, request, redirect, url_for, flash, send_file, session
from PIL import Image, ImageDraw, ImageFont

# --- 초기 설정 ---
app = Flask(__name__)
# session을 사용하려면 secret_key가 반드시 필요합니다.
app.secret_key = 'a_very_secret_key_for_session'

# 관리자 로그인 정보 (요청하신대로 설정)
ADMIN_USERNAME = 'tkeoehguq'
ADMIN_PASSWORD = '2025vhgkdrhdeo'

# 폴더 및 데이터베이스 경로 설정
BASE_DIR = '/home/Jeongsh/abcd1234' # ★ 본인의 아이디와 폴더명 확인
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')
RESOURCE_FOLDER = os.path.join(BASE_DIR, 'resources')
DATABASE_PATH = os.path.join(BASE_DIR, 'participants.db')

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def init_db():
    with sqlite3.connect(DATABASE_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS participants (
                email TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                institution TEXT NOT NULL
            )
        ''')
        conn.commit()

# --- 웹 페이지 라우팅 ---

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            session['logged_in'] = True
            flash('로그인 성공!')
            return redirect(url_for('admin'))
        else:
            flash('아이디 또는 비밀번호가 올바르지 않습니다.')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    flash('로그아웃 되었습니다.')
    return redirect(url_for('lookup'))

@app.route('/admin')
def admin():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    return render_template('admin.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
        
    if 'file' not in request.files:
        flash('파일이 없습니다.')
        return redirect(url_for('admin'))
    
    file = request.files['file']
    if file.filename == '':
        flash('파일을 선택해주세요.')
        return redirect(url_for('admin'))

    if file:
        filepath = os.path.join(UPLOAD_FOLDER, file.filename)
        file.save(filepath)
        try:
            df = pd.read_excel(filepath)
            if not {'이름', '기관', '이메일'}.issubset(df.columns):
                flash("엑셀 파일에 '이름', '기관', '이메일' 컬럼이 모두 필요합니다.")
                return redirect(url_for('admin'))
            
            with sqlite3.connect(DATABASE_PATH) as conn:
                cursor = conn.cursor()
                cursor.execute('DELETE FROM participants')
                for index, row in df.iterrows():
                    cursor.execute(
                        'INSERT INTO participants (email, name, institution) VALUES (?, ?, ?)',
                        (row['이메일'], row['이름'], row['기관'])
                    )
                conn.commit()

            flash(f'{len(df)}명의 참가자 정보가 데이터베이스에 영구적으로 저장되었습니다.')
            return redirect(url_for('admin'))
        
        except Exception as e:
            flash(f'파일 처리 중 오류 발생: {e}')
            return redirect(url_for('admin'))
    
    return redirect(url_for('admin'))

@app.route('/')
def lookup():
    return render_template('lookup.html')

@app.route('/certificate')
def certificate_view():
    email = request.args.get('email')
    if not email:
        return redirect(url_for('lookup'))
    
    user_info = None
    with sqlite3.connect(DATABASE_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT name, institution FROM participants WHERE email = ?', (email,))
        user_info = cursor.fetchone()

    if not user_info:
        flash('등록되지 않은 이메일입니다. 다시 확인해주세요.')
        return redirect(url_for('lookup'))
    
    name, institution = user_info
    return render_template('certificate_view.html', name=name, email=email)


@app.route('/generate_image')
def generate_image():
    email = request.args.get('email')
    
    user_info = None
    with sqlite3.connect(DATABASE_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT name, institution FROM participants WHERE email = ?', (email,))
        user_info = cursor.fetchone()

    if not user_info:
        return "Invalid request", 400

    name, institution = user_info

    image = Image.open(os.path.join(RESOURCE_FOLDER, '참가확인증_2025001.png')).convert("RGBA")
    draw = ImageDraw.Draw(image)
    font_path = os.path.join(RESOURCE_FOLDER, 'NanumMyeongjoBold.ttf')
    font = ImageFont.truetype(font_path, 22)
    text_color = "black"

    draw.text((290, 340), institution, font=font, fill=text_color)
    draw.text((290, 400), name, font=font, fill=text_color)
    
    img_io = io.BytesIO()
    image.save(img_io, 'PNG')
    img_io.seek(0)
    
    return send_file(img_io, mimetype='image/png')

init_db()

if __name__ == '__main__':
    app.run(debug=True)