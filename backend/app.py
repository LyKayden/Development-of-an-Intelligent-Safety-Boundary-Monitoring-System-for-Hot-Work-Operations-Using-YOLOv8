# backend/app.py
"""
Flask 后端主程序
功能：视频流处理、WebSocket 通信、API 接口
"""

from flask import Flask, send_from_directory, Response, request, jsonify
from flask_socketio import SocketIO, emit
# 修改 1：生产模式可移除 CORS（同源部署不需要）
# from flask_cors import CORS
import cv2
import threading
import time
import os
import torch
from engine import SafetyRuleEngine
from config import CAMERA_F0, INFER_SIZE, VIDEO_WIDTH, VIDEO_HEIGHT, VIDEO_FPS

# 使用相对路径
current_dir = os.path.dirname(os.path.abspath(__file__))

# 修改 2：前端静态文件目录（生产模式）
frontend_dist = os.path.join(current_dir, '..', 'frontend', 'dist')

# 修改 3：Flask 配置（移除 static_folder，只配置 template_folder）
app = Flask(__name__, template_folder=frontend_dist)  # 只配置前端页面目录
app.config['SECRET_KEY'] = 'hotwork_monitor_2026'

# 修改 4：生产模式移除 CORS（同源部署不需要）
# CORS(app, resources={r"/*": {"origins": "*"}})

# SocketIO 配置
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

# 全局变量
engine = None
cap = None
is_running = False

# 双帧缓冲（关键架构：分离捕获和处理）
frame_lock = threading.Lock()
raw_frame = None        # 原始帧（捕获线程写入）
processed_frame = None  # 处理后的帧（处理线程写入，视频流读取）
current_alarms = []

# 告警统计
alarm_stats = {
    'gas_to_gas': 0,
    'gas_to_fire': 0,
    'worker_violation': 0,
    'safety_line_missing': 0,
    'supervisor_missing': 0,
    'fire_extinguisher_missing': 0
}

# 性能监控（动态帧率统计）
perf_stats = {
    'frame_times': [],      # 处理时间列表（毫秒）
    'last_print_time': 0,   # 上次打印时间
    'total_frames': 0,      # 总处理帧数
    'start_time': 0         # 开始时间
}

def initialize_engine():
    """初始化测距引擎"""
    global engine
    engine = SafetyRuleEngine()

def video_capture_thread():
    """
    视频捕获线程（30 FPS）
    只负责读取摄像头，不进行 AI 处理
    """
    global cap, raw_frame

    while True:
        ret, frame = cap.read()
        if not ret:
            time.sleep(0.01)
            continue

        with frame_lock:
            raw_frame = frame.copy() # 只保留最新帧

        # 不 sleep，让摄像头全速运行

def video_processing_thread():
    """
    视频处理线程（固定帧率，避免 CPU 过载）

    工作流程：
    1. 未监控时：只转发原始画面（不 AI 推理）
    2. 监控时：完整处理（检测 + 距离 + 告警）
    """
    global raw_frame, processed_frame, current_alarms, is_running, alarm_stats, perf_stats

    perf_stats['start_time'] = time.time()
    perf_stats['last_print_time'] = time.time()

    while True:
        # 记录开始时间
        frame_start = time.time()

        # 获取原始帧
        with frame_lock:
            if raw_frame is None:
                time.sleep(0.01)
                continue
            frame = raw_frame.copy()

        # ========== 只在监控时进行 AI 推理 ==========
        if is_running:
            # AI 推理
            detections = engine.detect(frame)

            # 距离检查
            alarms = engine.check_distance(detections)
            current_alarms = alarms

            # 统计告警次数
            for alarm in alarms:
                alarm_type = alarm.get('type', 'unknown')
                if alarm_type in alarm_stats:
                    alarm_stats[alarm_type] += 1

            # 告警推送
            if alarms:
                for alarm in alarms:
                    socketio.emit('alarm', alarm)
                    print(f"[ALARM] [{alarm['type']}] {alarm['message']}")

            # 可视化绘制（检测框 + 连线 + 距离 + 告警）
            frame = engine.draw_visualization(frame, detections, alarms, is_running)
        else:
            # 未监控时：只添加提示文字，不 AI 推理
            alarms = []
            cv2.putText(frame, "Click to set fire point, then click Start",
                    (50, frame.shape[0]-50),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)

        # 写入处理后的帧
        with frame_lock:
            processed_frame = frame

        # ========== 性能监控（只在监控时统计） ==========
        if is_running:
            perf_stats['total_frames'] += 1
            frame_time = (time.time() - frame_start) * 1000
            perf_stats['frame_times'].append(frame_time)

            if len(perf_stats['frame_times']) > 100:
                perf_stats['frame_times'].pop(0)

            # 每 5 秒打印一次性能统计
            current_time = time.time()
            if current_time - perf_stats['last_print_time'] >= 5.0:
                avg_time = sum(perf_stats['frame_times']) / len(perf_stats['frame_times'])
                actual_fps = 1000 / avg_time if avg_time > 0 else 0
                elapsed = current_time - perf_stats['start_time']

                print("=" * 60)
                print("📊 [PERF] 性能统计")
                print(f"   运行时间：{elapsed:.1f}秒")
                print(f"   总处理帧数：{perf_stats['total_frames']}帧")
                print(f"   平均处理时间：{avg_time:.1f}ms/帧")
                print(f"   实际帧率：{actual_fps:.1f} FPS")
                print("=" * 60)

                perf_stats['last_print_time'] = current_time

        # # 添加 sleep 控制帧率
        # elapsed = time.time() - frame_start
        # sleep_time = max(0, DETECTION_INTERVAL - elapsed)
        # time.sleep(sleep_time)

def generate_frames():
    """
    视频流生成器（从 processed_frame 读取）
    从处理后的帧读取，才能看到检测框等绘制内容
    """
    while True:
        with frame_lock:
            # 从 processed_frame 读取（包含检测框、连线、动火点）
            if processed_frame is None:
                time.sleep(0.01)
                continue
            frame = processed_frame.copy()

        # 编码并发送（JPEG 质量 80，平衡清晰度和带宽）
        ret, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
        if not ret:
            continue

        frame_bytes = buffer.tobytes()

        yield (b'--frame\r\n'
            b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')

# 修改 5：首页路由（生产模式）
@app.route('/')
def index():
    """返回前端打包后的 index.html"""
    return send_from_directory(frontend_dist, 'index.html')

# 修改 6：前端静态资源路由（CSS/JS/音频等）
@app.route('/assets/<path:filename>')
def serve_assets(filename):
    """返回前端打包后的静态资源"""
    return send_from_directory(os.path.join(frontend_dist, 'assets'), filename)

@app.route('/audio/<path:filename>')
def serve_audio(filename):
    """返回音频文件"""
    return send_from_directory(os.path.join(frontend_dist, 'audio'), filename)

@app.route('/video')
def video():
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/start', methods=['POST'])
def start_task():
    """启动监控任务"""
    global is_running

    try:
        data = request.get_json()
        print("=" * 60)
        print("▶️ [API] 收到启动监控请求")
        print(f"   请求数据：{data}")
        print(f"   时间：{time.strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 60)

        if data:
            engine.set_fire_point(data.get('fire_point_x'), data.get('fire_point_y'))
            # 修改 7：米转换为毫米
            platform_height_m = data.get('platform_height', 0.0)
            platform_height_mm = platform_height_m * 1000
            engine.set_platform_height(platform_height_mm)
            print(f"   平台高度差：{platform_height_m}米 = {platform_height_mm}毫米")


        is_running = True
        print("✅ [SYSTEM] 监控已启动")
        return jsonify({'status': 'started', 'message': 'Monitoring started'})
    except Exception as e:
        print(f"[ERROR] 启动失败：{e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/stop', methods=['POST'])
def stop_task():
    """停止监控任务"""
    global is_running
    is_running = False
    print("=" * 60)
    print("⏹️ [SYSTEM] 监控已停止")
    print(f"   时间：{time.strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    return jsonify({'status': 'stopped', 'message': 'Monitoring stopped'})

@app.route('/set_fire_point', methods=['POST'])
def set_fire_point():
    """设置动火点"""
    try:
        data = request.get_json()
        print("=" * 60)
        print("📍 [API] 收到动火点设置请求")
        print(f"   请求数据：{data}")
        print(f"   时间：{time.strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 60)

        engine.set_fire_point(data.get('x'), data.get('y'))

        return jsonify({'status': 'success'})
    except Exception as e:
        print(f"[ERROR] 设置动火点失败：{e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/clear_fire_point', methods=['POST'])
def clear_fire_point():
    """清除动火点"""
    try:
        print("=" * 60)
        print("🗑️ [API] 收到清除动火点请求")
        print(f"   时间：{time.strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 60)

        engine.clear_fire_point()

        return jsonify({'status': 'success'})
    except Exception as e:
        print(f"[ERROR] 清除动火点失败：{e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/set_platform_height', methods=['POST'])
def set_platform_height():
    """设置平台高度"""
    data = request.json
    engine.set_platform_height(data.get('height', 0.0))
    return jsonify({'status': 'success'})

@app.route('/stats')
def get_stats():
    """获取告警统计"""
    return jsonify(alarm_stats)

@app.route('/reset_stats', methods=['POST'])
def reset_stats():
    """重置告警统计"""
    global alarm_stats
    alarm_stats = {
        'gas_to_gas': 0,
        'gas_to_fire': 0,
        'worker_violation': 0,
        'safety_line_missing': 0,
        'supervisor_missing': 0,
        'fire_extinguisher_missing': 0
    }
    return jsonify({'status': 'reset'})

if __name__ == '__main__':
    # 初始化引擎
    initialize_engine()

    # 打开摄像头
    cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)

    # 设置摄像头参数（与标定时一致：1280x720 @ 30fps）
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, VIDEO_WIDTH)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, VIDEO_HEIGHT)
    cap.set(cv2.CAP_PROP_FPS, VIDEO_FPS)

    if not cap.isOpened():
        print("Cannot open camera, please check connection")
        exit(1)

    print(f"✅ Camera opened: 1280x720 @ 30fps")
    print(f"✅ f0={CAMERA_F0} (与标定一致)")
    print(f"✅ 视频流从 processed_frame 读取")
    print(f"✅ 性能统计：每 5 秒打印一次")
    if torch.cuda.is_available():
        print(f"✅ GPU Device: {torch.cuda.get_device_name(0)}")
    print(f"✅ 模型设备：{engine.model.device}")  # 显示 GPU 信息

    # 启动双线程
    threading.Thread(target=video_capture_thread, daemon=True).start()
    threading.Thread(target=video_processing_thread, daemon=True).start()

    # 启动服务器
    print("=" * 60)
    print("Server: http://localhost:5000")
    # 修改 8：生产模式，前端由 Flask 托管（移除 5173 端口显示）
    print("✅ 生产模式：前端由 Flask 托管（无需 Node.js）")
    print("=" * 60)

    # 启动 Flask 服务器
    socketio.run(app, host='0.0.0.0', port=5000, debug=False)
