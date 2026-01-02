import sys, os

# Thêm thư mục hiện tại vào đường dẫn hệ thống
sys.path.append(os.getcwd())

# Import app từ file app.py của bạn
# 'app' đầu tiên là tên file (app.py)
# 'app' thứ hai là tên biến Flask (app = Flask(__name__))
from app import app as application