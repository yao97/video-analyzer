# -*- mode: python ; coding: utf-8 -*-

"""
现代化 PyInstaller 打包配置
适配 PyInstaller 6.0+ 版本
"""

from PyInstaller.utils.hooks import collect_all, collect_data_files, collect_submodules
from PyInstaller.building.build_main import Analysis, COLLECT, EXE
from os.path import join, basename, dirname, exists
from os import walk, makedirs
from shutil import copyfile, rmtree


# 初始化空列表
binaries = []
hiddenimports = []
datas = []

# 隐藏导入 - 确保所有需要的模块都被包含
hiddenimports += [
    'rich',
    'rich.console',
    'rich.markdown',
    'rich._unicode_data.unicode17-0-0',
    'numpy',
    'typer',
    'srt',
]


a = Analysis(
    ['transcribe.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=['build_hook.py'],
    excludes=['torch', 'transformers', ],
    noarchive=False,
    optimize=0,
)



# 排除不要打包的模块（这些将作为源文件复制）
private_module = ['qwen_asr_gguf', 
                  ]
pure = a.pure.copy()
a.pure.clear()
for name, src, type in pure:
    condition = [name == m or name.startswith(m + '.') for m in private_module]
    if condition and any(condition):
        ...
    else:
        a.pure.append((name, src, type))



pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='transcribe',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,

    # 所有第三方依赖放入 internal 目录
    contents_directory = 'internal', 
    icon = 'assets/icon.ico'
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='Qwen3-ASR-Transcribe',
)



# 复制额外所需的文件（只复制用户自己写的文件）
my_files = [
    'readme.md'
]
my_folders = []     # 这里是要复制的文件夹
dest_root = join('dist', basename(coll.name))

# 复制文件夹中的文件
for folder in my_folders:
    if not exists(folder):
        continue
    for dirpath, dirnames, filenames in walk(folder):
        for filename in filenames:
            src_file = join(dirpath, filename)
            if exists(src_file):
                my_files.append(src_file)

# 执行文件复制到根目录（不是 internal）
for file in my_files:
    if not exists(file):
        continue
    # 保持相对路径结构
    rel_path = file.replace('\\', '/') if '\\' in file else file
    dest_file = join(dest_root, rel_path)
    dest_folder = dirname(dest_file)
    makedirs(dest_folder, exist_ok=True)
    copyfile(file, dest_file)


# 为 models 文件夹建立链接，免去复制大文件
from platform import system
from subprocess import run

if system() == 'Windows':
    link_folders = ['qwen_asr_gguf', 'model']  # 不再链接 util，因为 util 已经被复制
    for folder in link_folders:
        if not exists(folder):
            continue
        dest_folder = join(dest_root, folder)
        if exists(dest_folder):
            rmtree(dest_folder)
        # 使用管理员权限运行的命令提示符来创建目录连接符
        cmd = ['mklink', '/j', dest_folder, folder]
        try:
            run(cmd, shell=True, check=True)
        except:
            print(f'警告：无法创建目录连接符 {dest_folder}，请手动创建或复制文件夹')