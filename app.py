import os
import pandas as pd
import io
import sqlite3 # 데이터베이스를 위해 추가
from flask import Flask, render_template, request, redirect, url_for, flash, send_file
from PIL import Image, ImageDraw, ImageFont

# --- 초기 설정 ---
app = Flask(__name__)
app.secret_key = 'supersecretkey_for_db'

# 폴더 및 데이터베이스 경로 설정
# PythonAnywhere 서버의 전체 경로를 사용해야 합니다.
BASE_DIR = '/home/Jeongsh/abcd1234' # ★ 본인의 아이디와 폴더명 확인
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')
RESOURCE_FOLDER = os.path.join(BASE_DIR, 'resources')
DATABASE_PATH = os.path.join(BASE_DIR, 'participants.db') # 데이터베이스 파일 경로

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# === 데이터베이스 관련 코드 추가 ===
def init_db():
    """앱 시작 시 데이터베이스와 테이블이 없으면 생성"""
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
@app.route('/admin')
def admin():
    return render_template('admin.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    """엑셀 파일을 업로드하고 데이터를 데이터베이스에 저장합니다."""
    if 'file' not in request.files:
        flash('파일이 없습니다.'); return redirect(url_for('admin'))
    
    file = request.files['file']
    if file.filename == '':
        flash('파일을 선택해주세요.'); return redirect(url_for('admin'))

    if file:
        filepath = os.path.join(UPLOAD_FOLDER, file.filename)
        file.save(filepath)
        try:
            df = pd.read_excel(filepath)
            if not {'이름', '기관', '이메일'}.issubset(df.columns):
                flash("엑셀 파일에 '이름', '기관', '이메일' 컬럼이 모두 필요합니다."); return redirect(url_for('admin'))
            
            # 데이터베이스에 연결
            with sqlite3.connect(DATABASE_PATH) as conn:
                cursor = conn.cursor()
                # 기존 명단을 모두 지웁니다 (업데이트를 위해).
                cursor.execute('DELETE FROM participants')
                # 새 명단을 데이터베이스에 추가합니다.
                for index, row in df.iterrows():
                    cursor.execute(
                        'INSERT INTO participants (email, name, institution) VALUES (?, ?, ?)',
                        (row['이메일'], row['이름'], row['기관'])
                    )
                conn.commit()

            flash(f'{len(df)}명의 참가자 정보가 데이터베이스에 영구적으로 저장되었습니다.')
            return redirect(url_for('admin'))
        
        except Exception as e:
            flash(f'파일 처리 중 오류 발생: {e}'); return redirect(url_for('admin'))
    
    return redirect(url_for('admin'))

@app.route('/')
def lookup():
    return render_template('lookup.html')

@app.route('/certificate')
def certificate_view():
    email = request.args.get('email')
    if not email: return redirect(url_for('lookup'))
    
    user_info = None
    with sqlite3.connect(DATABASE_PATH) as conn:
        cursor = conn.cursor()
        # 데이터베이스에서 이메일로 참가자 조회
        cursor.execute('SELECT name, institution FROM participants WHERE email = ?', (email,))
        user_info = cursor.fetchone()

    if not user_info:
        flash('등록되지 않은 이메일입니다.