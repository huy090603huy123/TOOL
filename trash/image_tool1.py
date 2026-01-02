import os
import re
import threading
import subprocess
import sys
from PIL import Image

import tkinter as tk
from tkinter import scrolledtext, messagebox, filedialog, ttk as regular_ttk
import ttkbootstrap as ttk
from ttkbootstrap.scrolled import ScrolledText
from ttkbootstrap.constants import *

# --- HÀM HỖ TRỢ ĐƯỜNG DẪN MAC/APP ---
def get_base_path():
    """
    Hàm này xác định vị trí thực tế của ứng dụng.
    - Nếu chạy script .py: Lấy thư mục chứa file script.
    - Nếu chạy file đóng gói .app (macOS): Lấy thư mục chứa file .app (để để suffixes.txt bên cạnh).
    """
    if getattr(sys, 'frozen', False):
        # Đang chạy dạng đóng gói (PyInstaller)
        application_path = os.path.dirname(sys.executable)
        if sys.platform == "darwin":
            # Trên Mac, sys.executable nằm trong ImageTool.app/Contents/MacOS/
            # Ta lùi ra 3 cấp để về thư mục chứa file .app
            application_path = os.path.abspath(os.path.join(application_path, "../../.."))
        return application_path
    else:
        # Đang chạy file .py bình thường
        return os.path.dirname(os.path.abspath(__file__))

# ------------------- CẤU HÌNH -------------------
# Tự động lấy thư mục Downloads của người dùng hiện tại trên Mac
THU_MUC_MAC_DINH = os.path.join(os.path.expanduser("~"), "Downloads")

# File suffixes.txt sẽ nằm cùng thư mục với file chạy
BASE_PATH = get_base_path()
SUFFIX_CONFIG_FILE = os.path.join(BASE_PATH, "suffixes.txt")

QUALITY_PERCENT = 50
TARGET_WIDTH_NGANG = 1080
TARGET_WIDTH_DOC = 640
DINH_DANG_ANH_HOP_LE = (
    '.png', '.gif', '.bmp', '.tiff', '.webp', '.heic',
    '.heif', '.ico', '.pcx', '.ppm', '.sgi', '.tga',
    '.jpg', '.jpeg', '.image'
)
# -------------------------------------------------

# --- HÀM LOGIC & HELPER ---
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
    text = text.strip('-')
    return text

def tim_so_thu_tu_tiep_theo(thu_muc, ten_goc, suffix):
    so_lon_nhat = 0
    mau_regex = re.compile(f"^{re.escape(ten_goc)}{re.escape(suffix)}-(\\d+)\\.jpeg$", re.IGNORECASE)
    try:
        for ten_file in os.listdir(thu_muc):
            ket_qua = mau_regex.match(ten_file)
            if ket_qua:
                so_hien_tai = int(ket_qua.group(1))
                if so_hien_tai > so_lon_nhat:
                    so_lon_nhat = so_hien_tai
    except OSError:
        pass
    return so_lon_nhat + 1

def xu_ly_hang_loat(thu_muc, ten_goc, suffix, logger_func):
    try:
        stt_bat_dau = tim_so_thu_tu_tiep_theo(thu_muc, ten_goc, suffix)
        cac_file_can_xu_ly = []
        
        # Lọc file
        for ten_file in os.listdir(thu_muc):
            if ten_file.lower().endswith(DINH_DANG_ANH_HOP_LE):
                da_xu_ly = False
                # Bỏ qua các file đã có format đúng kiểu output
                mau_da_xu_ly = re.compile(f"^{re.escape(ten_goc)}{re.escape(suffix)}-\\d+\\.jpeg$", re.IGNORECASE)
                if mau_da_xu_ly.match(ten_file):
                    da_xu_ly = True

                if not da_xu_ly:
                    cac_file_can_xu_ly.append(ten_file)
        
        if not cac_file_can_xu_ly:
            logger_func("-> Không tìm thấy ảnh mới nào để xử lý.")
            return

        logger_func(f"-> Tìm thấy {len(cac_file_can_xu_ly)} ảnh. Bắt đầu xử lý với tên '{ten_goc}', hậu tố '{suffix}' và STT từ {stt_bat_dau}...")
        so_luong_thanh_cong = 0
        
        for ten_file_goc in cac_file_can_xu_ly:
            duong_dan_goc = os.path.join(thu_muc, ten_file_goc)
            ten_file_moi = f"{ten_goc}{suffix}-{stt_bat_dau}.jpeg"
            duong_dan_moi = os.path.join(thu_muc, ten_file_moi)
            
            try:
                with Image.open(duong_dan_goc) as img:
                    width, height = img.size
                    da_resize = False

                    if width > height and width > TARGET_WIDTH_NGANG:
                        new_width = TARGET_WIDTH_NGANG
                        new_height = int((new_width / width) * height)
                        img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
                        logger_func(f"   - Resized (ngang): {width}x{height} -> {new_width}x{new_height}")
                        da_resize = True
                    elif height >= width and width > TARGET_WIDTH_DOC:
                        new_width = TARGET_WIDTH_DOC
                        new_height = int((new_width / width) * height)
                        img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
                        logger_func(f"   - Resized (dọc): {width}x{height} -> {new_width}x{new_height}")
                        da_resize = True

                    if img.mode in ("RGBA", "P"):
                        img = img.convert('RGB')

                    img.save(duong_dan_moi,
                             'jpeg',
                             quality=QUALITY_PERCENT,
                             optimize=True,
                             progressive=True,
                             subsampling=2)
                    
                    log_prefix = "Đã resize, nén" if da_resize else "Đã nén (giữ kích thước)"
                    logger_func(f"   -> {log_prefix} & đổi tên: '{ten_file_goc}' -> '{ten_file_moi}'")

                os.remove(duong_dan_goc)
                stt_bat_dau += 1
                so_luong_thanh_cong += 1
            except Exception as e:
                logger_func(f"   *** Lỗi khi xử lý file {ten_file_goc}: {e}")
                
        logger_func(f"-> HOÀN THÀNH: Đã xử lý thành công {so_luong_thanh_cong}/{len(cac_file_can_xu_ly)} ảnh.")
    except Exception as e:
        logger_func(f"*** Đã xảy ra lỗi nghiêm trọng trong quá trình xử lý: {e}")

# --- LỚP GIAO DIỆN ĐỒ HỌA (GUI) ---
class ImageProcessorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Công cụ xử lý ảnh hàng loạt (Mac Optimized)")
        self.root.geometry("800x600") 

        main_frame = ttk.Frame(self.root, padding="15")
        main_frame.pack(fill="both", expand=True)

        # --- Vùng chọn thư mục ---
        dir_frame = ttk.Frame(main_frame)
        dir_frame.grid(row=0, column=0, columnspan=3, sticky="ew", pady=(0, 10))
        
        ttk.Label(dir_frame, text="Thư mục xử lý:").pack(side=LEFT, padx=(0, 5))
        
        self.selected_directory = tk.StringVar()
        if os.path.isdir(THU_MUC_MAC_DINH):
            self.selected_directory.set(os.path.abspath(THU_MUC_MAC_DINH))
        else:
            self.selected_directory.set(os.path.abspath(os.path.expanduser("~")))
        
        self.dir_entry = ttk.Entry(dir_frame, textvariable=self.selected_directory, state="readonly")
        self.dir_entry.pack(side=LEFT, fill="x", expand=True, padx=5)
        
        self.change_dir_button = ttk.Button(
            dir_frame,
            text="Thay đổi... 📂", 
            command=self.chon_thu_muc,
            bootstyle="secondary" 
        )
        self.change_dir_button.pack(side=LEFT)

        # --- Vùng nhập tên ---
        ttk.Label(main_frame, text="Nhập tên gốc:").grid(row=1, column=0, sticky="w", padx=5, pady=5)
        
        self.name_var = tk.StringVar()
        self.entry_name = ttk.Entry(main_frame, width=50, textvariable=self.name_var)
        self.entry_name.grid(row=1, column=1, sticky="ew", padx=5, pady=5)
        self.name_var.trace_add("write", self.auto_format_name_entry)

        # --- VÙNG HẬU TỐ (SUFFIX) ---
        suffix_frame = ttk.LabelFrame(main_frame, text="Quản lý Đuôi")
        suffix_frame.grid(row=1, column=2, sticky="ns", padx=(10, 5), pady=0, rowspan=2)

        self.suffixes = self.load_suffixes_from_file()

        ttk.Label(suffix_frame, text="Chọn Đuôi:").grid(row=0, column=0, sticky="w", padx=5, pady=(5,0))

        self.suffix_var = tk.StringVar()
        self.suffix_combobox = ttk.Combobox(
            suffix_frame,
            textvariable=self.suffix_var,
            values=self.suffixes,
            state="readonly"
        )
        self.suffix_combobox.grid(row=1, column=0, sticky="ew", padx=5, pady=2)
        if self.suffixes:
            self.suffix_var.set(self.suffixes[0])

        ttk.Label(suffix_frame, text="Hoặc thêm Đuôi mới:").grid(row=2, column=0, sticky="w", padx=5, pady=(10,0))
        
        self.new_suffix_var = tk.StringVar()
        self.new_suffix_entry = ttk.Entry(
            suffix_frame,
            textvariable=self.new_suffix_var
        )
        self.new_suffix_entry.grid(row=3, column=0, sticky="ew", padx=5, pady=2)

        self.add_suffix_button = ttk.Button(
            suffix_frame,
            text="Thêm vào danh sách",
            command=self.add_new_suffix,
            bootstyle="info-outline"
        )
        self.add_suffix_button.grid(row=4, column=0, sticky="ew", padx=5, pady=5)
        
        suffix_frame.columnconfigure(0, weight=1)

        # --- Vùng nút ---
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=2, column=0, columnspan=2, pady=10)
        
        self.process_button = ttk.Button(
            button_frame, 
            text="Xử lý ảnh 🚀", 
            command=self.start_processing_thread,
            bootstyle="success"
        )
        self.process_button.pack(side=LEFT, padx=5)
        
        self.open_folder_button = ttk.Button(
            button_frame, 
            text="Mở thư mục 📁", 
            command=self.open_folder,
            bootstyle="info-outline"
        )
        self.open_folder_button.pack(side=LEFT, padx=5)

        # --- Vùng log ---
        self.log_area = ScrolledText(main_frame, wrap=tk.WORD, height=15, autohide=True)
        self.log_area.grid(row=3, column=0, columnspan=3, sticky="nsew")

        main_frame.columnconfigure(1, weight=1)
        main_frame.columnconfigure(2, weight=0)
        main_frame.rowconfigure(3, weight=1)

        self.log_message(f"Hệ điều hành: macOS")
        self.log_message(f"File cấu hình đuôi: {SUFFIX_CONFIG_FILE}")
        self.log_message(f"Sẵn sàng xử lý tại: {self.selected_directory.get()}\n" + "="*50)
    
    def load_suffixes_from_file(self):
        # Đảm bảo file tồn tại trước khi đọc
        if not os.path.exists(SUFFIX_CONFIG_FILE):
             try:
                with open(SUFFIX_CONFIG_FILE, 'w', encoding='utf-8') as f:
                    # Ghi một giá trị mặc định nếu file chưa có
                    f.write("-thuvienmovie\n")
             except Exception as e:
                 print(f"Không thể tạo file config: {e}")
                 return ["-thuvienmovie"]

        try:
            with open(SUFFIX_CONFIG_FILE, 'r', encoding='utf-8') as f:
                suffixes = [line.strip() for line in f if line.strip()]
            if not suffixes:
                return ["-thuvienmovie"]
            return suffixes
        except Exception:
            return ["-thuvienmovie"]
    
    def save_suffixes_to_file(self):
        try:
            with open(SUFFIX_CONFIG_FILE, 'w', encoding='utf-8') as f:
                for suffix in self.suffixes:
                    f.write(suffix + '\n')
        except Exception as e:
            self.log_message(f"*** Lỗi khi lưu file hậu tố tại {SUFFIX_CONFIG_FILE}: {e}")

    def add_new_suffix(self):
        suffix_raw = self.new_suffix_var.get().strip()
        if not suffix_raw:
            messagebox.showerror("Lỗi", "Hậu tố không được để trống!")
            return

        suffix = format_as_slug(suffix_raw)
        if not suffix:
            messagebox.showerror("Lỗi", "Hậu tố không hợp lệ!")
            return
        
        if not suffix.startswith('-'):
            suffix = '-' + suffix

        if suffix not in self.suffixes:
            self.suffixes.insert(0, suffix)
            self.suffix_combobox['values'] = self.suffixes
            self.save_suffixes_to_file()
            self.log_message(f"-> Đã thêm và lưu hậu tố mới: '{suffix}'")
        else:
            self.log_message(f"-> Hậu tố '{suffix}' đã tồn tại.")

        self.suffix_var.set(suffix)
        self.new_suffix_var.set("")

    def chon_thu_muc(self):
        initial_dir = self.selected_directory.get()
        new_directory = filedialog.askdirectory(
            title="Chọn thư mục chứa ảnh cần xử lý",
            initialdir=initial_dir
        )
        
        if new_directory:
            self.selected_directory.set(os.path.abspath(new_directory))
            self.log_message(f"\nĐã thay đổi thư mục xử lý thành:\n{self.selected_directory.get()}\n" + "="*50)
        else:
            self.log_message("-> Thao tác chọn thư mục đã bị hủy.")

    def auto_format_name_entry(self, *args):
        current_text = self.name_var.get()
        formatted_text = format_as_slug(current_text)

        if current_text != formatted_text:
            cursor_pos = self.entry_name.index(tk.INSERT)
            self.name_var.set(formatted_text)
            self.entry_name.icursor(cursor_pos)

    def log_message(self, message):
        self.log_area.insert(tk.END, message + "\n")
        self.log_area.see(tk.END)
        self.root.update_idletasks()

    def open_folder(self):
        current_dir = self.selected_directory.get()
        if os.path.isdir(current_dir):
            try:
                # Lệnh mở thư mục chuẩn trên macOS
                subprocess.Popen(["open", current_dir])
            except Exception as e:
                messagebox.showerror("Lỗi", f"Không thể mở thư mục: {e}")
        else:
            messagebox.showwarning("Cảnh báo", "Thư mục đã chọn không tồn tại.")
            
    def start_processing_thread(self):
        base_name = self.name_var.get().strip()
        directory = self.selected_directory.get()
        suffix = self.suffix_var.get()
        
        if not suffix:
            messagebox.showerror("Lỗi", "Vui lòng chọn một hậu tố (suffix)!")
            return

        if not base_name:
            messagebox.showerror("Lỗi", "Tên gốc không được để trống!")
            return
        
        if not directory or not os.path.isdir(directory):
            messagebox.showerror("Lỗi", f"Thư mục xử lý không hợp lệ:\n{directory}")
            return
            
        self.process_button.config(state="disabled")
        self.change_dir_button.config(state="disabled")
        self.add_suffix_button.config(state="disabled")
        self.new_suffix_entry.config(state="disabled")
        self.suffix_combobox.config(state="disabled")
        
        thread = threading.Thread(target=self.run_processing, args=(base_name, directory, suffix))
        thread.start()

    def run_processing(self, base_name, directory, suffix):
        self.log_message(f"\nBắt đầu xử lý cho tên: '{base_name}'...")
        self.log_message(f"Sử dụng hậu tố: '{suffix}'")
        
        xu_ly_hang_loat(directory, base_name, suffix, self.log_message)
        
        self.process_button.config(state="normal")
        self.change_dir_button.config(state="normal")
        self.add_suffix_button.config(state="normal")
        self.new_suffix_entry.config(state="normal")
        self.suffix_combobox.config(state="readonly")


if __name__ == "__main__":
    # Theme flatly nhìn đẹp và hiện đại trên Mac
    root = ttk.Window(themename="flatly")
    app = ImageProcessorApp(root)
    root.mainloop()