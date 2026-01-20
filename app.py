import os
import re
import io
import zipfile
from flask import Flask, render_template, request, send_file, jsonify
# Thêm ImageEnhance để xử lý làm nét ảnh
from PIL import Image, ImageEnhance 

app = Flask(__name__)

# --- CẤU HÌNH ---
# Cho phép upload tối đa 500MB
app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024 

# CẤU HÌNH ẢNH ĐẦU RA
QUALITY_PERCENT = 85      # 85: Điểm cân bằng vàng giữa dung lượng thấp và mắt nhìn thấy đẹp
SHARPNESS_FACTOR = 1.3    # 1.0 là gốc. 1.2 giúp ảnh nét hơn sau khi bị resize nhỏ lại
TARGET_WIDTH_NGANG = 1280 # Kích thước cho ảnh ngang
TARGET_WIDTH_DOC = 640    # Kích thước cho ảnh dọc
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
    # Yêu cầu phải có file templates/index.html
    return render_template('index.html')

@app.route('/process', methods=['POST'])
def process_images():
    try:
        uploaded_files = request.files.getlist('images')
        base_name_raw = request.form.get('base_name', 'untitled')
        suffix = request.form.get('suffix', '-thuvienmovie')
        
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

                    # Logic: Chỉ resize nhỏ đi, không phóng to (để tránh vỡ ảnh)
                    if width > height: # Ảnh Ngang
                        if width > TARGET_WIDTH_NGANG:
                            new_width = TARGET_WIDTH_NGANG
                            new_height = int((new_width / width) * height)
                            needs_resize = True
                    else: # Ảnh Dọc hoặc Vuông
                        if width > TARGET_WIDTH_DOC:
                            new_width = TARGET_WIDTH_DOC
                            new_height = int((new_width / width) * height)
                            needs_resize = True
                    
                    # Thực hiện Resize
                    if needs_resize:
                        # LANCZOS: Thuật toán tốt nhất để giữ chi tiết khi thu nhỏ
                        img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)

                    # Chuyển đổi hệ màu (đề phòng ảnh trong suốt PNG hoặc hệ màu lạ)
                    if img.mode in ("RGBA", "P"):
                        img = img.convert('RGB')

                    # --- BƯỚC 2: TĂNG ĐỘ NÉT (SHARPEN) ---
                    # Giúp ảnh trông sắc nét hơn sau khi nén
                    enhancer = ImageEnhance.Sharpness(img)
                    img = enhancer.enhance(SHARPNESS_FACTOR)

                    # Tạo tên file mới
                    new_filename = f"{base_name}{suffix}-{stt}.jpeg"
                    
                    # --- BƯỚC 3: LƯU VÀ TỐI ƯU ---
                    img_byte_arr = io.BytesIO()
                    img.save(
                        img_byte_arr, 
                        format='JPEG', 
                        quality=QUALITY_PERCENT, # 85%
                        optimize=True,           # Nén sâu cấu trúc file
                        progressive=True,        # Tải dần trên web
                        subsampling=0            # Giữ nguyên thông tin màu (4:4:4) -> Nét căng, không bị loang lổ
                    )
                    img_byte_arr.seek(0)

                    # Ghi vào ZIP
                    zf.writestr(new_filename, img_byte_arr.getvalue())
                    
                    stt += 1
                    processed_count += 1
                    
                except Exception as e:
                    print(f"Lỗi khi xử lý file {file.filename}: {e}")

        if processed_count == 0:
            return jsonify({"error": "Không xử lý được ảnh nào (lỗi định dạng hoặc file hỏng)"}), 400

        memory_file.seek(0)
        
        response = send_file(
            memory_file,
            mimetype='application/zip',
            as_attachment=True,
            download_name=f'{base_name}-processed.zip'
        )
        # Header trả về số lượng ảnh đã xử lý (để client biết nếu cần)
        response.headers["X-Process-Log"] = str(processed_count)
        return response

    except Exception as e:
        print(f"Lỗi Server: {str(e)}")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    # Host 0.0.0.0 để truy cập được từ các máy khác trong cùng mạng LAN
    app.run(debug=True, host='0.0.0.0', port=5000)