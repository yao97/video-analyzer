#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
打包脚本 - 使用 7zip 压缩 dist 目录中的构建产物
"""

import os
import subprocess
from pathlib import Path
from datetime import datetime


def find_7zip():
    """查找 7zip 可执行文件"""
    possible_paths = [
        r"C:\Program Files\7-Zip\7z.exe",
        r"C:\Program Files (x86)\7-Zip\7z.exe",
    ]

    # 从 PATH 环境变量查找
    for path in os.environ.get("PATH", "").split(os.pathsep):
        possible_paths.append(os.path.join(path, "7z.exe"))

    for path in possible_paths:
        if os.path.exists(path):
            return path

    return None


def should_include_file(file_path):
    """
    判断文件是否应该被打包
    
    规则：
    - 排除 __pycache__, .vscode, .git 等
    - model 文件夹中，除了 .txt 文件外全部排除
    """
    path = Path(file_path)
    parts = path.parts

    # 1. 基础排除
    if any(p in parts for p in ('__pycache__', '.vscode', '.git')):
        return False

    # 2. model 文件夹特殊逻辑
    if 'model' in parts:
        # 如果是 model 文件夹内的文件，只保留 .txt
        if path.suffix.lower() != '.txt':
            return False

    return True


def create_file_list(dist_folder, output_file='file_list.txt'):
    """
    创建要打包的文件列表
    """
    files = []
    dist_path = Path(dist_folder)
    if not dist_path.exists():
        return files, None

    # 我们要打包的是 dist_folder 文件夹本身及其内容
    # 所以在压缩包中，顶层应该是 Qwen3-ASR-Transcribe 文件夹
    # 7zip 在 dist 目录下运行时，如果列表包含 Qwen3-ASR-Transcribe/xxx，则会按此结构打包
    
    parent_path = dist_path.parent
    
    for root, dirs, filenames in os.walk(dist_path):
        # 排除不需要打包的文件夹（用于 os.walk 剪枝）
        dirs[:] = [d for d in dirs if d not in ('__pycache__', '.vscode', '.git')]

        for filename in filenames:
            file_path = os.path.join(root, filename)
            if should_include_file(file_path):
                # 计算相对于 dist 目录（即 parent_path）的路径
                rel_path = os.path.relpath(file_path, parent_path)
                files.append(rel_path)

    if not files:
        return files, None

    # 写入文件列表
    list_file = Path(output_file)
    list_file.write_text('\n'.join(files), encoding='utf-8')

    return files, list_file


def package_with_7zip(source_dir, output_zip, file_list_file):
    """使用 7zip 打包目录"""

    seven_zip = find_7zip()
    if not seven_zip:
        raise FileNotFoundError(
            "找不到 7zip。请确认已安装 7-Zip。\n"
            "下载地址: https://www.7-zip.org/"
        )

    source_path = Path(source_dir)
    dist_dir = source_path.parent
    
    # 确保输出目录存在
    output_path = Path(output_zip)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # 文件列表路径
    list_file_abs = Path(file_list_file).absolute()
    # 7zip 从 dist_dir 运行，所以列表路径要相对于 dist_dir
    list_file_rel_to_dist = os.path.relpath(list_file_abs, dist_dir)

    # 构建 7zip 命令
    cmd = [
        seven_zip,
        'a',                      # 添加
        '-tzip',                  # ZIP 格式
        '-mx9',                   # 最大压缩
        str(output_path.absolute()),
        f'@{list_file_rel_to_dist}',
    ]

    print(f"\n正在打包: {source_path.name}")
    print(f"输出文件: {output_zip}")
    print(f"工作目录: {dist_dir.absolute()}")

    # 执行压缩
    result = subprocess.run(
        cmd,
        cwd=str(dist_dir),
        capture_output=True,
        text=True,
        encoding='utf-8',
        errors='ignore'
    )

    if result.returncode != 0:
        print(f"\n错误: 7zip 执行失败")
        print(f"STDOUT: {result.stdout}")
        print(f"STDERR: {result.stderr}")
        raise subprocess.CalledProcessError(result.returncode, cmd)

    print("\n✅ 打包成功！")


def main():
    """主函数"""
    dist_dir = Path('dist') / 'Qwen3-ASR-Transcribe'

    if not dist_dir.exists():
        print(f"错误: 目录不存在: {dist_dir}")
        return

    print("=" * 60)
    print("Qwen3-ASR 打包导出脚本")
    print("=" * 60)

    # 构建输出目录
    release_dir = Path('release')
    release_dir.mkdir(exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d")
    output_zip = release_dir / f'Qwen3-ASR-Transcribe-{timestamp}.zip'

    try:
        # 1. 生成文件列表
        list_file_name = 'file_list_release.txt'
        files, list_file = create_file_list(dist_dir, list_file_name)

        if not files:
            print(f"\n没有找到要打包的文件")
            return

        print(f"打包文件数: {len(files)}")

        # 2. 打包
        package_with_7zip(dist_dir, output_zip, list_file)

        # 3. 清理
        if list_file.exists():
            list_file.unlink()

    except Exception as e:
        print(f"\n打包失败: {e}")

    print(f"\n{'=' * 60}")
    print(f"输出目录: {release_dir.absolute()}")
    if output_zip.exists():
        size_mb = output_zip.stat().st_size / (1024 * 1024)
        print(f"生成文件: {output_zip.name} ({size_mb:.2f} MB)")


if __name__ == '__main__':
    main()
