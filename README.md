# 🔥 动火作业智能监控系统

**本科毕业设计项目 - 动火作业现场智能安全监控**

基于 YOLOv8 目标检测 + 单目视觉测距 + GB 30871-2022 安全规范

> **⚠️ 许可证声明 / License**
> The source code is licensed under MIT. The trained model weights in the `models/` directory are derived from Ultralytics YOLOv8 and are subject to the AGPL-3.0 license.

---

## 📋 系统要求

### 必需软件（用户需自行安装）

|
 软件
|
 版本
|
 下载地址
|
 用途
|
|
---
|
---
|
---
|
---
|
|
 Miniconda
|
 Python 3.11+
|

[
下载链接
](
https://docs.conda.io/en/latest/miniconda.html
)
|
 Python 环境管理
|
|
 Node.js
|
 18.x LTS
|

[
下载链接
](
https://nodejs.org/zh-cn/
)
|
 前端运行环境
|
|
 Windows
|
 10/11
|
 -
|
 操作系统
|

### 推荐硬件

|
 配置
|
 要求
|
 说明
|
|
---
|
---
|
---
|
|
 CPU
|
 Intel i5 或同级
|
 4 核以上
|
|
 内存
|
 8GB 以上
|
 推荐 16GB
|
|
 显卡
|
 NVIDIA GTX 1060 以上
|
 支持 CUDA 加速（MX450 及以上）
|
|
 摄像头
|
 720P/1080P
|
 USB 或网络摄像头
|

### 性能参考

|
 设备
|
 帧率
|
 处理时间
|
|
---
|
---
|
---
|
|
 NVIDIA MX450
|
 25-30 FPS
|
 33-40ms/帧
|
|
 NVIDIA RTX 3060
|
 40-60 FPS
|
 17-25ms/帧
|
|
 CPU (i5-11320H)
|
 10-15 FPS
|
 67-100ms/帧
|

---

## 🚀 快速开始

### 步骤 1：安装基础环境（首次使用）

**安装 Miniconda**
- 下载：https://docs.conda.io/en/latest/miniconda.html
- 安装时勾选 "Add to PATH"
- 安装完成后重启电脑

**安装 Node.js**
- 下载：https://nodejs.org/zh-cn/
- 选择 LTS 版本（长期支持版）
- 默认安装即可（npm 自动附带）

### 步骤 2：安装项目依赖

```bash
# 双击 install.bat
# 或手动执行：
cd HotworkMonitor
install.bat
等待安装完成（约 5-10 分钟，取决于网速）

步骤 3：启动系统
# 双击 start.bat
# 或手动执行：
start.bat
浏览器会自动打开 http://localhost:5173/

步骤 4：使用系统
等待视频流加载完成
输入平台高度差（地面作业填 0）
点击视频画面锚定动火点位置
点击 "开始监控" 按钮
系统自动检测气瓶并计算安全距离
🛡️ 安全规则（GB 30871-2022）
距离规则（实时检测，每帧处理）
规则	要求	告警类型	音频
氧气瓶与乙炔瓶间距	≥ 5 米	🔴 严重告警	✅ 播放
氧气瓶与动火点间距	≥ 10 米	🔴 严重告警	✅ 播放
乙炔瓶与动火点间距	≥ 10 米	🔴 严重告警	✅ 播放
存在规则（间隔检测，降低告警疲劳）
规则	要求	检测间隔	告警类型	音频
警戒线设置	必须存在	5 秒（125 帧）	🟡 警告告警	❌ 静音
监护人到位	必须存在	6 秒（150 帧）	🟡 警告告警	❌ 静音
灭火器配备	必须存在	6 秒（150 帧）	🟡 警告告警	❌ 静音
工人违规行为	实时检测	3 秒（75 帧）	🔴 严重告警	✅ 播放
注：基于 25 FPS 实际帧率计算，间隔帧数 = 目标秒数 × 25

颜色标识
目标	检测框颜色	说明
氧气瓶	🔵 蓝色	符合行业标准
乙炔瓶	🔴 红色	符合行业标准
警戒线	🟡 黄色	醒目提示
监护人	🟣 紫色	区分普通工人
灭火器	🟠 橙色	醒目提示
安全工人	🟢 绿色	正常状态
违规工人	🔴 红色	违规行为
📁 项目结构
HotworkMonitor/
├── install.bat              # 一键安装脚本
├── start.bat                # 一键启动脚本（生产模式）
├── stop.bat                 # 一键停止脚本
├── README.md                # 使用说明
│
├── backend/                 # 后端代码（Python + Flask）
│   ├── app.py               # Flask 主程序
│   ├── engine.py            # 测距引擎（核心算法）
│   ├── config.py            # 配置文件
│   ├── calibrate_f0.py      # 相机标定脚本
│   └── requirements.txt     # Python 依赖
│
├── frontend/                # 前端代码（Vue3 + Vite）
│   ├── src/                 # 源代码（开发时用）
│   │   ├── App.vue          # 主界面
│   │   └── ...
│   ├── public/
│   │   └── audio/
│   │       └── alarm.mp3    # 告警音效
│   ├── package.json         # Node.js 依赖
│   └── dist/                # 打包后生成（生产时用）
│       ├── index.html
│       ├── assets/
│       └── audio/
│
└── models/                  # AI 模型
    └── best.pt              # YOLOv8 训练模型（PyTorch 格式）
🏗️ 系统架构
┌─────────────────────────────────────────────────────────────┐
│                    双线程架构                                │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  捕获线程 (30 FPS)          处理线程 (GPU 全速)               │
│  ┌──────────────┐          ┌──────────────┐                │
│  │  读摄像头     │          │  AI 推理       │                │
│  │  ↓           │          │  距离计算     │                │
│  │  raw_frame   │─────────→│  绘制         │                │
│  └──────────────┘          │  ↓           │                │
│                            │  processed   │                │
│                            └──────────────┘                │
│                                   ↓                         │
│                            ┌──────────────┐                │
│                            │  视频流生成   │                │
│                            │  (MJPEG)     │                │
│                            │  读 processed│  ✅ 能看到检测框  │
│                            └──────────────┘                │
│                                                             │
│  前端 (Vue3)               WebSocket 通信                    │
│  ┌──────────────┐          ┌──────────────┐                │
│  │  视频播放     │←─────────│  告警推送     │                │
│  │  动火点绘制   │          │  状态同步     │                │
│  │  告警显示     │          │              │                │
│  └──────────────┘          └──────────────┘                │
│                                                             │
└─────────────────────────────────────────────────────────────┘
关键技术
技术	说明
YOLOv8	目标检测模型（7 类目标）
单目测距	基于相机标定的三维坐标重建
GPU 加速	CUDA 加速推理（MX450 可达 30 FPS）
双帧缓冲	捕获/处理分离，避免卡顿
WebSocket	实时告警推送
前端绘制	动火点标记 60+ FPS 丝滑显示
⚙️ 配置说明
backend/config.py

# 相机内参（需标定）
CAMERA_F0 = 684          # 等效焦距
CAMERA_CX = 640          # 图像中心 X
CAMERA_CY = 360          # 图像中心 Y

# 安全距离阈值（毫米）
GAS_TO_GAS_THRESHOLD = 5000     # 5 米
GAS_TO_FIRE_THRESHOLD = 10000   # 10 米

# 间隔检测配置（帧数，基于 25 FPS）
SAFETY_LINE_CHECK_INTERVAL = 125       # 5 秒
SUPERVISOR_CHECK_INTERVAL = 150        # 6 秒
FIRE_EXTINGUISHER_CHECK_INTERVAL = 150 # 6 秒
WORKER_VIOLATION_CHECK_INTERVAL = 75   # 3 秒

# 告警推送间隔（秒）
ALARM_INTERVAL = 5.0  # 相同告警最小推送间隔

# 检测阈值
CONFIDENCE_THRESHOLD = 0.25  # 置信度阈值
NMS_IOU_THRESHOLD = 0.45     # NMS 阈值

# 推理分辨率
INFER_SIZE = 320  # 降低分辨率提升速度
🔧 常见问题
Q: install.bat 运行失败？
A:

检查是否已安装 Miniconda 和 Node.js
以管理员身份运行脚本
检查网络连接（需要下载依赖）
Q: start.bat 提示找不到 conda？
A: 编辑 start.bat，手动指定 conda 安装路径：

call "C:\Users\你的用户名\miniconda3\Scripts\activate.bat" yolov8
Q: 视频流不显示？
A:

检查摄像头是否被其他程序占用
刷新浏览器（Ctrl+F5）
检查后端是否正常运行（查看命令行窗口）
Q: 检测效果不好？
A:

改善光照条件（最重要！）
运行 backend/calibrate_f0.py 重新标定相机参数
调整摄像头角度和焦距
Q: 告警太频繁？
A:

存在规则已采用间隔检测（5-6 秒）
可调整 config.py 中的检测间隔配置
告警推送间隔为 5 秒，避免频闪
Q: 没有告警声音？
A:

检查 frontend/public/audio/alarm.mp3 是否存在
只有紧急告警（红色）才播放音频
检查浏览器是否静音
Q: GPU 没有启用？
A:

检查是否安装 PyTorch GPU 版本
运行 python -c "import torch; print(torch.cuda.is_available())"
如显示 False，需重新安装 PyTorch CUDA 版本
Q: 帧率太低？
A:

检查是否使用 GPU 加速
降低推理分辨率（INFER_SIZE = 320）
关闭其他占用 GPU 的程序
📊 性能优化建议
光照条件
✅ 充足光照可大幅提升检测率
❌ 暗光环境下检测率下降 50% 以上
摄像头位置
✅ 正对作业区域
✅ 高度 2-3 米为宜
❌ 避免逆光拍摄
系统配置
✅ 使用 GPU 加速（MX450 及以上）
✅ 推理分辨率 320x320
✅ 关闭其他占用 GPU 的程序
📞 技术支持
如有问题，请联系开发者或查看项目文档。

📝 更新日志
版本	日期	更新内容
v2.0	2026-05	GPU 加速、音频告警、间隔检测优化
v1.0	2026-04	初始版本，CPU 推理
📄 许可证
The source code is licensed under MIT. The trained model weights in the models/ directory are derived from Ultralytics YOLOv8 and are subject to the AGPL-3.0 license.

本科毕业设计项目，仅供学习使用。 ```
