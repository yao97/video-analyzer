import sys
import os
from os.path import dirname, join, exists

# 将「执行文件所在目录」添加到「模块查找路径」
# 这确保了可以找到从项目根目录直接拷贝过来的 .py 文件/包
executable_dir = dirname(sys.executable)
sys.path.insert(0, executable_dir)

# PyInstaller 打包时，第三方依赖（DLL, PYD）放在 internal/ 目录
# 虽然 PyInstaller 6+ 会自动处理，但手动确保 root 和 internal 都在路径中更保险
internal_dir = join(executable_dir, 'internal')
if exists(internal_dir):
    sys.path.insert(0, internal_dir)
