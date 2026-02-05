import os
import re
import io
import zipfile
from flask import Flask, render_template, request, send_file, jsonify
from PIL import Image, ImageEnhance 

app = Flask(__name__)

# --- CẤU HÌNH ---
app.config['MAX_CONTENT_LENGTH'] = 2048 * 1024 * 1024 

# CẤU HÌNH ẢNH ĐẦU RA
QUALITY_PERCENT = 85      
SHARPNESS_FACTOR = 1.3    

# Kích thước mặc định
TARGET_WIDTH_NGANG = 1080 
TARGET_WIDTH_DOC = 640    

# Kích thước tùy chọn mới
TARGET_WIDTH_OPTION = 1280 

DINH_DANG_ANH_HOP_LE = ('.png', '.gif', '.bmp', '.tiff', '.webp', '.heic', '.heif', '.ico', '.jpg', '.jpeg')

# --- HÀM XỬ LÝ TÊN FILE (SLUG) ---
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
        
        # --- BỔ SUNG: Kiểm tra xem người dùng có tick chọn 1280px không ---
        # Nếu checkbox được tick, biến này sẽ là True
        use_1280_mode = 'resize_1280' in request.form 

        if not uploaded_files:
            return jsonify({"error": "Không có file nào được gửi lên"}), 400

        # Chuẩn hóa tên file
        base_name = format_as_slug(base_name_raw)
        if not suffix.startswith('-'): suffix = '-' + suffix

        memory_file = io.BytesIO()
        processed_count = 0

        # Mở file ZIP để ghi
        with zipfile.ZipFile(memory_file, 'w', zipfile.ZIP_DEFLATED) as zf:
            stt = 1
            for file in uploaded_files:
                if file.filename == '': continue
                
                # Kiểm tra đuôi file
                ext = os.path.splitext(file.filename)[1].lower()
                if ext not in DINH_DANG_ANH_HOP_LE:
                    print(f"Bỏ qua định dạng không hỗ trợ: {ext}")
                    continue

                try:
                    img = Image.open(file)
                    width, height = img.size
                    
                    # --- BƯỚC 1: TÍNH TOÁN RESIZE ---
                    new_width, new_height = width, height
                    needs_resize = False

                    # Logic: Chỉ resize nhỏ đi, không phóng to
                    
                    if width > height: # Ảnh Ngang
                        # Nếu chọn mode 1280 thì dùng 1280, không thì dùng 1080
                        target_w = TARGET_WIDTH_OPTION if use_1280_mode else TARGET_WIDTH_NGANG
                        
                        if width > target_w:
                            new_width = target_w
                            new_height = int((new_width / width) * height)
                            needs_resize = True
                    else: # Ảnh Dọc hoặc Vuông
                        # Ảnh dọc thường giữ nguyên 640px kể cả khi chọn mode 1280 
                        # (trừ khi bạn muốn ảnh dọc cũng to lên thì sửa dòng dưới thành TARGET_WIDTH_OPTION)
                        if width > TARGET_WIDTH_DOC:
                            new_width = TARGET_WIDTH_DOC
                            new_height = int((new_width / width) * height)
                            needs_resize = True
                    
                    # Thực hiện Resize
                    if needs_resize:
                        img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)

                    # Chuyển đổi hệ màu
                    if img.mode in ("RGBA", "P"):
                        img = img.convert('RGB')

                    # --- BƯỚC 2: TĂNG ĐỘ NÉT (SHARPEN) ---
                    enhancer = ImageEnhance.Sharpness(img)
                    img = enhancer.enhance(SHARPNESS_FACTOR)

                    # Tạo tên file mới
                    new_filename = f"{base_name}{suffix}-{stt}.jpeg"
                    
                    # --- BƯỚC 3: LƯU VÀ TỐI ƯU ---
                    img_byte_arr = io.BytesIO()
                    img.save(
                        img_byte_arr, 
                        format='JPEG', 
                        quality=QUALITY_PERCENT,
                        optimize=True,          
                        progressive=True,       
                        subsampling=0           
                    )
                    img_byte_arr.seek(0)

                    # Ghi vào ZIP
                    zf.writestr(new_filename, img_byte_arr.getvalue())
                    
                    stt += 1
                    processed_count += 1
                    
                except Exception as e:
                    print(f"Lỗi khi xử lý file {file.filename}: {e}")

        if processed_count == 0:
            return jsonify({"error": "Không xử lý được ảnh nào"}), 400

        memory_file.seek(0)
        
        response = send_file(
            memory_file,
            mimetype='application/zip',
            as_attachment=True,
            download_name=f'{base_name}-processed.zip'
        )
        response.headers["X-Process-Log"] = str(processed_count)
        return response

    except Exception as e:
        print(f"Lỗi Server: {str(e)}")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)