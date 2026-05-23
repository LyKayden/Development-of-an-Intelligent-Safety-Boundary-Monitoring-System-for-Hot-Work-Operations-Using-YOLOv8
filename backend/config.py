# backend/config.py
"""
系统配置文件
相机参数需要根据实际摄像头标定
标定方法：运行 calibrate_f0.py 脚本

"""

# ========== 相机内参 ==========
# 通过 calibrate_f0.py 标定得到
# 不同摄像头下不同分辨率需要重新标定
CAMERA_F0 = 684      # 等效像素焦距（根据标定结果修改）
CAMERA_CX = 640       # 图像中心 X (1280/2)
CAMERA_CY = 360       # 图像中心 Y (720/2)

# ========== 气瓶标准高度（毫米） ==========
OXYGEN_CYLINDER_HEIGHT = 1500      # 1.5 米 = 1500 毫米
ACETYLENE_CYLINDER_HEIGHT = 1500   # 1.5 米 = 1500 毫米

# ========== 安全距离阈值（毫米） ==========
# 根据 GB 30871-2022 标准
GAS_TO_GAS_THRESHOLD = 5000        # 5 米 = 5000 毫米
GAS_TO_FIRE_THRESHOLD = 10000      # 10 米 = 10000 毫米

# ========== 间隔检测配置（帧数） ==========
# 降低计算负载，避免告警疲劳
# 基于实际平均帧率 25 FPS 计算
# 公式：间隔帧数 = 目标秒数 × 25 FPS
SAFETY_LINE_CHECK_INTERVAL = 125       # 警戒线检测间隔（5 秒）静态物体
SUPERVISOR_CHECK_INTERVAL = 150        # 监护人检测间隔（6 秒）人可能走动
FIRE_EXTINGUISHER_CHECK_INTERVAL = 150 # 灭火器检测间隔（6 秒）静态物体
WORKER_VIOLATION_CHECK_INTERVAL = 75  # 违规工人检测间隔（3 秒）人可能走动

# ========== 告警推送间隔（秒） ==========
# 避免告警频闪，相同告警间隔推送
# 相同告警的最小推送间隔（应该 < 前端显示时间）
ALARM_INTERVAL = 5.0

# ========== 服务器配置 ==========
HOST = "0.0.0.0" # 绑定所有网络接口
PORT = 5000 # 服务端口

# ========== 检测置信度阈值 ==========
CONFIDENCE_THRESHOLD = 0.25  # Ultralytics 默认值

# ========== NMS 阈值 ==========
NMS_IOU_THRESHOLD = 0.45     # 非极大值抑制阈值

# ========== 推理分辨率 ==========
INFER_SIZE = 320  # 从 640 降到 320，速度提升 4 倍

# ========== 视频参数 ==========
VIDEO_WIDTH = 1280
VIDEO_HEIGHT = 720
VIDEO_FPS = 30
