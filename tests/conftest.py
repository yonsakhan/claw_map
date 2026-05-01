import os
import sys


# 让测试在“未安装成包”的情况下也能 `import src.*`
# pytest 会把该文件所在目录加入 sys.path，但项目根目录不一定在其中。
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

