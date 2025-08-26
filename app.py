import os
import pandas as pd
import io
from flask import Flask, render_template, request, redirect, url_for, flash, send_file
from PIL import Image, ImageDraw, ImageFont

# --- 초기 설정 ---
app = Flask(__name__)
app.secret_key = 'supersecretkey_for_v2'

# 폴더 설정
UPLOAD_FOLDER = 'uploads'
RESOURCE_FOLDER = 'resources'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

participants_df = None

# --- 웹 페이지 라우팅 ---
@app.route('/admin')
def admin():
    return render_template('admin.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    global participants_df
    if 'file' not in request.files:
        flash('파일이 없습니다.'); return redirect(url_for('admin'))
    file = request.files['file']
    if file.filename == '':
        flash('파일을 선택해주세요.'); return redirect(url_for('admin'))
    if file:
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
        file.save(filepath)
        try:
            df = pd.read_excel(filepath)
            if not {'이름', '기관', '이메일'}.issubset(df.columns):
                flash("엑셀 파일에 '이름', '기관', '이메일' 컬럼이 모두 필요합니다."); return redirect(url_for('admin'))
            participants_df = df.set_index('이메일')
            flash(f'{len(participants_df)}명의 참가자 정보가 성공적으로 등록되었습니다.'); return redirect(url_for('admin'))
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
    if participants_df is None or email not in participants_df.index:
        flash('등록되지 않은 이메일입니다. 다시 확인해주세요.'); return redirect(url_for('lookup'))
    user_info = participants_df.loc[email]
    return render_template('certificate_view.html', name=user_info['이름'], email=email)

# --- 이미지 생성 API ---
@app.route('/generate_image')
def generate_image():
    email = request.args.get('email')
    if participants_df is None or email not in participants_df.index:
        return "Invalid request", 400

    user_info = participants_df.loc[email]
    name = user_info['이름']
    institution = user_info['기관']

    # --- ★★★ 이 부분을 직접 수정하세요 ★★★ ---
    # 1. 템플릿 이미지 파일 경로 설정 (resources 폴더에 넣어둔 이미지 파일 이름과 똑같이!)
    template_path = os.path.join(RESOURCE_FOLDER, '참가확인증_2025001.png')
    
    # 2. 이미지를 직접 엽니다.
    image = Image.open(template_path).convert("RGBA")
    draw = ImageDraw.Draw(image)

    # 3. 폰트와 색상 설정 (resources 폴더에 넣어둔 폰트 파일 이름과 똑같이!)
    font_path = os.path.join(RESOURCE_FOLDER, 'NanumMyeongjoBold.ttf')
    font_size = 22
    font = ImageFont.truetype(font_path, font_size)
    text_color = "black"

    # 4. 텍스트 위치 설정 (가장 중요!)
    inst_position = (280, 341)
    name_position = (280, 398)

    # 5. 텍스트 그리기
    draw.text(inst_position, institution, font=font, fill=text_color)
    draw.text(name_position, name, font=font, fill=text_color)
    # ------------------------------------------
    
    img_io = io.BytesIO()
    image.save(img_io, 'PNG')
    img_io.seek(0)
    
    return send_file(img_io, mimetype='image/png')

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')