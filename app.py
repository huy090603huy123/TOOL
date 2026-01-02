import os
import re
import io
import zipfile
from flask import Flask, render_template, request, send_file, jsonify
from PIL import Image

app = Flask(__name__)

# --- CẤU HÌNH ---
QUALITY_PERCENT = 50
TARGET_WIDTH_NGANG = 1080
TARGET_WIDTH_DOC = 640
DINH_DANG_ANH_HOP_LE = ('.png', '.gif', '.bmp', '.tiff', '.webp', '.heic', '.heif', '.ico', '.jpg', '.jpeg')

# --- HÀM HELPER ---
def format_as_slug(text):
    text = text.lower()
    vietnamese_map = {
        'á': 'a', 'à': 'a', 'ả': 'a', 'ã': 'a', 'ạ': 'a', 'ă': 'a', 'ắ': 'a', 'ằ': 'a', 'ẳ': 'a', 'ẵ': 'a', 'ặ': 'a', 'â': 'a', 'ấ': 'a', 'ầ': 'a', 'ẩ': 'a', 'ẫ': 'a', 'ậ': 'a',
        'đ': 'd',
        'é': 'e', 'è': 'e', 'ẻ': 'e', 'ẽ': 'e', 'ẹ': 'e', 'ê': 'e', 'ế': 'e', 'ề': 'e', 'ể': 'e', 'ễ': 'e', 'ệ': 'e',
        'í': 'i', 'ì': 'i', 'ỉ': 'i', 'ĩ': 'i', 'ị': 'i',
        'ó': 'o', 'ò': 'o', 'ỏ': 'o', 'õ': 'o', 'ọ': 'o', 'ô': 'o', 'ố': 'o', 'ồ': 'o', 'ổ': 'o', 'ỗ': 'o', 'ộ': 'o', 'ơ': 'o', 'ớ': 'o', 'ờ': 'o', 'ở': 'o', 'ỡ': 'o', 'ợ': 'o',
        'ú': 'u', 'ù': 'u', 'ủ': 'u', 'ũ': 'u', 'ụ': 'u', 'ư': 'u', 'ứ': 'u', 'ừ': 'u', 'ử': 'u', 'ữ': 'u', 'ự': 'u',
        'ý': 'y', 'ỳ': 'y', 'ỷ': 'y', 'ỹ': 'y', 'ỵ': 'y'
    }
    for char, replacement in vietnamese_map.items():
        text = text.replace(char, replacement)
    text = re.sub(r'[^a-z0-9\s-]', '', text)
    text = re.sub(r'\s+', '-', text)
    return text.strip('-')

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/process', methods=['POST'])
def process_images():
    try:
        uploaded_files = request.files.getlist('images')
        base_name_raw = request.form.get('base_name', 'untitled')
        suffix = request.form.get('suffix', '-thuvienmovie')
        
        # Xử lý input
        base_name = format_as_slug(base_name_raw)
        if not suffix.startswith('-'): suffix = '-' + suffix

        # Bộ nhớ đệm cho file ZIP đầu ra
        memory_file = io.BytesIO()
        
        processed_count = 0
        logs = []

        with zipfile.ZipFile(memory_file, 'w', zipfile.ZIP_DEFLATED) as zf:
            stt = 1
            for file in uploaded_files:
                if file.filename == '': continue
                
                ext = os.path.splitext(file.filename)[1].lower()
                if ext not in DINH_DANG_ANH_HOP_LE:
                    continue

                try:
                    img = Image.open(file)
                    width, height = img.size
                    
                    # Logic Resize
                    new_width, new_height = width, height
                    if width > height and width > TARGET_WIDTH_NGANG:
                        new_width = TARGET_WIDTH_NGANG
                        new_height = int((new_width / width) * height)
                        img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
                    elif height >= width and width > TARGET_WIDTH_DOC:
                        new_width = TARGET_WIDTH_DOC
                        new_height = int((new_width / width) * height)
                        img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)

                    if img.mode in ("RGBA", "P"):
                        img = img.convert('RGB')

                    # Tạo tên mới
                    new_filename = f"{base_name}{suffix}-{stt}.jpeg"
                    
                    # Lưu ảnh đã xử lý vào buffer
                    img_byte_arr = io.BytesIO()
                    img.save(img_byte_arr, format='JPEG', quality=QUALITY_PERCENT, optimize=True, progressive=True, subsampling=2)
                    img_byte_arr.seek(0)

                    # Ghi vào file ZIP
                    zf.writestr(new_filename, img_byte_arr.getvalue())
                    
                    stt += 1
                    processed_count += 1
                    
                except Exception as e:
                    print(f"Error processing {file.filename}: {e}")

        memory_file.seek(0)
        
        response = send_file(
            memory_file,
            mimetype='application/zip',
            as_attachment=True,
            download_name=f'{base_name}-processed.zip'
        )
        # Header log để JS đọc
        response.headers["X-Process-Log"] = str(processed_count)
        return response

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)