import os
import sys

# 让 tests/ 里的用例能 import 到仓库根目录的 security.py / core.py
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
