# backend/calibrate_f0.py
"""
相机等效像素焦距 f0 标定脚本
使用方法：
1. 拍摄标定图片
2. 测量物体像素高度 h_calib
3. 输入 Z_measure 和 H
4. 计算 f0
"""

import os
import re

def calibrate_f0():
    print("=" * 60)
    print("相机等效像素焦距 f0 标定")
    print("=" * 60)

    # 输入标定参数
    print("\n请输入标定参数：")
    Z_measure = float(input("相机到物体的 Z 轴距离 Z_measure (米): "))
    H = float(input("物体实际高度 H (米): "))
    h_calib = float(input("物体在图像中的像素高度 h_calib (pixel): "))

    # 计算 f0
    f0 = Z_measure * h_calib / H

    print("\n" + "=" * 60)
    print("标定结果：")
    print("=" * 60)
    print(f"Z_measure = {Z_measure:.2f} 米")
    print(f"H = {H:.2f} 米")
    print(f"h_calib = {h_calib:.2f} pixel")
    print(f"\n等效像素焦距 f0 = {f0:.2f} pixel")
    print("=" * 60)

    # 保存到配置文件
    save = input("\n是否保存到 config.py? (y/n): ")
    if save.lower() == 'y':
        update_config(f0)
        print("✓ 已保存到 config.py")

    return f0

def update_config(f0):
    """更新 config.py 中的 CAMERA_F0"""
    # 使用相对路径（相对于当前脚本所在目录）
    current_dir = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(current_dir, 'config.py')

    print(f"配置文件路径：{config_path}")

    # 检查文件是否存在
    if not os.path.exists(config_path):
        print(f"❌ 错误：找不到配置文件 {config_path}")
        return

    with open(config_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # 替换 CAMERA_F0 值
    content = re.sub(r'CAMERA_F0 = \d+', f'CAMERA_F0 = {int(f0)}', content)

    with open(config_path, 'w', encoding='utf-8') as f:
        f.write(content)

    print(f"✓ CAMERA_F0 已更新为：{int(f0)}")

if __name__ == "__main__":
    calibrate_f0()
