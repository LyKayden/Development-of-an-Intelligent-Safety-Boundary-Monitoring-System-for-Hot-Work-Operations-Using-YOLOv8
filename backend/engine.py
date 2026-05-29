# backend/engine.py
"""
安全规则引擎
核心功能：目标检测 + 距离计算 + 告警判断 + 可视化绘制

使用 Ultralytics 官方 API（自动 GPU 加速）

实现 GB 30871-2022《危险化学品企业特殊作业安全规范》气瓶和动火点安全距离规范要求
"""

import cv2
import numpy as np
import os
import time
from ultralytics import YOLO  # 使用 Ultralytics 的 API
from config import *

class SafetyRuleEngine:
    """安全规则引擎类"""

    def __init__(self):
        """初始化引擎"""
        print("=" * 60)
        print("Initializing Safety Rule Engine...")
        print("=" * 60)

        # 1. 加载 YOLO 模型
        current_dir = os.path.dirname(os.path.abspath(__file__))
        model_path = os.path.join(current_dir, '..', 'models', 'best.pt') # 使用 PT 模型
        model_path = os.path.abspath(model_path)

        print(f"Loading model: {model_path}")

        if not os.path.exists(model_path):
            print(f"ERROR: Model file not found: {model_path}")
            raise FileNotFoundError(f"Model file not found: {model_path}")

        # 检查 CUDA 是否可用并强制使用 GPU（只加载一次）
        import torch
        print(f"🔍 CUDA available: {torch.cuda.is_available()}")
        if torch.cuda.is_available():
            print(f"🔍 GPU Device: {torch.cuda.get_device_name(0)}")
            self.model = YOLO(model_path)
            self.model.to('cuda:0')  # 强制移动到 GPU
            print(f"✅ Model loaded on: {self.model.device}")
        else:
            print("⚠️ CUDA not available, using CPU")
            self.model = YOLO(model_path) # CPU 加载
            print(f"✅ Model loaded on: {self.model.device}")

        # # 使用 Ultralytics 官方 API
        # self.model = YOLO(model_path)

        # # 确认设备
        # device = self.model.device
        # print(f"✅ Model loaded on: {device}")

        # 2. 相机参数
        self.f0 = CAMERA_F0
        self.cx = CAMERA_CX
        self.cy = CAMERA_CY
        print(f"OK: Camera params: f0={self.f0}, cx={self.cx}, cy={self.cy}")

        # 3. 气瓶高度配置（毫米）
        self.gas_heights = {
            2: OXYGEN_CYLINDER_HEIGHT,
            5: ACETYLENE_CYLINDER_HEIGHT
        }

        # 4. 安全阈值（毫米）
        self.thresholds = {
            'gas_to_gas': GAS_TO_GAS_THRESHOLD,
            'gas_to_fire': GAS_TO_FIRE_THRESHOLD
        }

        # 5. 动火点坐标
        self.fire_point = None

        # 6. 平台高度差（毫米）
        self.platform_height = 0.0

        # 7. 平面基准
        self.y_plane_base = 0.0
        self.y_plane_calc = 0.0

        # 8. 类别名称（7 类）
        self.class_names = [
            'worker_safe',      # 0
            'supervisor',       # 1
            'oxygen_cylinder',  # 2
            'fire_extinguisher',# 3
            'worker_violation', # 4
            'acetylene_cylinder',# 5
            'safety_line'       # 6
        ]

        # 9. 帧计数器
        self.frame_count = 0

        # 10. 告警状态
        self.last_alarm_time = {
            'gas_to_gas': 0,
            'gas_to_fire': 0,
            'safety_line_missing': 0,
            'supervisor_missing': 0,
            'fire_extinguisher_missing': 0,
            'worker_violation': 0
        }
        self.alarm_interval = ALARM_INTERVAL

        print("=" * 60)
        print("Engine initialization complete!")
        print("=" * 60)

        # 模型 Warmup
        self._warmup_model()

    def _warmup_model(self):
        """模型 Warmup"""
        print("🔥 Warming up model...")
        test_img = np.zeros((720, 1280, 3), dtype=np.uint8)
        self.detect(test_img)
        print("✅ Model warmup complete!")

    def detect(self, frame):
        """目标检测（使用 Ultralytics 官方 API）"""
        orig_h, orig_w = frame.shape[:2]

        # 使用官方 API（设置 GPU 加速 + 后处理 + NMS）
        # imgsz=320 降低分辨率提升速度
        results = self.model.predict(
            source=frame,
            imgsz=INFER_SIZE,       # 降低分辨率（320x320）
            conf=CONFIDENCE_THRESHOLD,
            iou=NMS_IOU_THRESHOLD,
            verbose=False,
            device=self.model.device,
            stream=False
        )

        # 解析结果
        detections = []
        result = results[0]
        boxes = result.boxes

        if boxes is not None:
            for i in range(len(boxes)):
                box = boxes[i]
                cls = int(box.cls[0])
                conf = float(box.conf[0])
                xyxy = box.xyxy[0].cpu().numpy()  # [x1, y1, x2, y2]
                # ↑ Ultralytics YOLOv8 的 xyxy 已经是像素坐标（相对于原始图像）
                # 不是归一化坐标！不需要对应乘以图像高度和宽度！

                x1, y1, x2, y2 = xyxy
                x1 = max(0, min(x1, orig_w))
                y1 = max(0, min(y1, orig_h))
                x2 = max(0, min(x2, orig_w))
                y2 = max(0, min(y2, orig_h))

                class_name = self.class_names[cls] if cls < len(self.class_names) else f'class_{cls}'

                detections.append({
                    'class': cls,
                    'class_name': class_name,
                    'box': [x1, y1, x2, y2],
                    'confidence': conf,
                    'center': [(x1 + x2) / 2, (y1 + y2) / 2],
                    'height': y2 - y1 # 这就是像素高度（单位：pixel）
                })

        self.frame_count += 1

        # # 调试信息
        # if self.frame_count % 50 == 0:
        #     print(f"[DETECT] 帧{self.frame_count}: 检测到{len(detections)}个目标")

        return detections

    def get_3d_point(self, u, v, h_pixel, H_real=None):
        """
        三维坐标重建（单目测距）

        使用检测框中心坐标（更稳定、收敛性好）
        - 气瓶：式 2-14
        - 动火点：式 2-18 ~ 2-22（射线 - 平面相交）

        参数：
        - u, v: 像素坐标
        - h_pixel: 物体像素高度
        - H_real: 物体实际高度（毫米）

        返回：(X, Y, Z) 相机坐标系下的三维坐标（毫米）
        """
        # 步骤 1：计算未归一化投影向量（式 2-18）
        # 减去主点，转换到以图像中心主点为原点
        vx = (u - self.cx) / self.f0
        vy = (v - self.cy) / self.f0
        vz = 1.0

        # 步骤 2：向量归一化（式 2-16、2-17）
        L = np.sqrt(vx**2 + vy**2 + vz**2)
        dx = vx / L
        dy = vy / L
        dz = vz / L

        # 情况 A：已知高度的物体（如气瓶）- 式 2-14
        if H_real and h_pixel:
            # 通过相似三角形，转换到相机三维坐标系（原点在光心）
            Z = self.f0 * (H_real / h_pixel) # 深度（单位：毫米）
            X = (u - self.cx) * Z / self.f0 # 相机坐标系 X（单位：毫米）
            Y = (v - self.cy) * Z / self.f0 # 相机坐标系 Y（单位：毫米）
            return np.array([X, Y, Z]) # 原点为相机光心

        # 情况 B：动火点（射线 - 平面相交）- 式 2-21、2-22
        else:
            # 检查平面是否有效
            if self.y_plane_calc is None or abs(self.y_plane_calc) < 1e-6:
                return None

            # 射线与平面相交（式 2-18）
            # 平面方程：Y + Dfinal = 0（相机水平安装：相机摄像头面垂直于水平地面，法向量n=(0,1,0)）
            # 射线方程：P(t) = t * d（d 为单位方向向量）
            # 联立得：t * dy + Dfinal = 0 → t = -Dfinal / dy
            # 其中 Dfinal = -self.y_plane_calc（y_plane_calc 是平面 Y 坐标）
            t = self.y_plane_calc / dy

            # 计算三维坐标（式 2-22）
            X = t * dx
            Y = t * dy
            Z = t * dz

            return np.array([X, Y, Z])

    def check_distance(self, detections):
        """距离检查与告警判断"""
        alarms = []
        current_time = time.time()

        oxygen_boxes = [d for d in detections if d['class'] == 2]
        acetylene_boxes = [d for d in detections if d['class'] == 5]

        # ========== 更新平面基准（式 2-16、2-17） ==========
        if oxygen_boxes:
            b = oxygen_boxes[0]
            u1, v1 = b['center'] # 使用检测框中心
            h1 = b['height']

            # 计算气瓶三维坐标（式 2-14）
            p1 = self.get_3d_point(u1, v1, h1, self.gas_heights[2])

            if p1 is not None:
                # Dbase = -Yc1（式 2-16，作业水平面法向量n=(0,1,0)）
                # 法向量 n = (0, 1, 0)（水平面假设）
                # 平面上一点 P1(Xc1, Yc1, Zc1)

                #
                # 计算 Dbase
                # Dbase = -(nx*Xc1 + ny*Yc1 + nz*Zc1)
                #    = -(0*Xc1 + 1*Yc1 + 0*Zc1)
                #    = -Yc1
                #
                Dbase = -p1[1] # p1[1] 就是 Yc1

                # Dfinal = Dbase + ΔD（式 2-17）
                #        = -Yc1 + Δh
                # platform_height 是高度差（毫米），直接相加
                self.y_plane_calc = Dbase + self.platform_height

                print(f"[PLANE] 平面基准更新：Y={self.y_plane_calc:.2f}mm")

        # ========== 规则 1: 氧气瓶与乙炔瓶间距（式 2-23） ==========
        for o_box in oxygen_boxes:
            for a_box in acetylene_boxes:
                dist = self._calc_distance(o_box, a_box)
                if dist and dist < self.thresholds['gas_to_gas']:
                    if current_time - self.last_alarm_time['gas_to_gas'] >= self.alarm_interval:
                        alarms.append({
                            'type': 'gas_to_gas',
                            'distance': dist,
                            'message': f'WARNING: Gas cylinders too close: {dist/1000:.2f}m < 5m'
                        })
                        self.last_alarm_time['gas_to_gas'] = current_time

        # ========== 规则 2: 气瓶与动火点间距（式 2-23） ==========
        if self.fire_point and self.y_plane_calc is not None:
            for b in oxygen_boxes + acetylene_boxes:
                dist = self._calc_distance_to_fire(b)
                if dist and dist < self.thresholds['gas_to_fire']:
                    if current_time - self.last_alarm_time['gas_to_fire'] >= self.alarm_interval:
                        bottle_type = "Oxygen" if b['class'] == 2 else "Acetylene"
                        alarms.append({
                            'type': 'gas_to_fire',
                            'distance': dist,
                            'message': f'WARNING: {bottle_type} too close to fire point: {dist/1000:.2f}m < 10m'
                        })
                        self.last_alarm_time['gas_to_fire'] = current_time

        # 规则 3: 警戒线
        if self.frame_count % SAFETY_LINE_CHECK_INTERVAL == 0:
            if not any(d['class'] == 6 for d in detections):
                if current_time - self.last_alarm_time['safety_line_missing'] >= self.alarm_interval:
                    alarms.append({
                        'type': 'safety_line_missing',
                        'distance': 0,
                        'message': 'WARNING: Safety line not detected!'
                    })
                    self.last_alarm_time['safety_line_missing'] = current_time

        # 规则 4: 监护人
        if self.frame_count % SUPERVISOR_CHECK_INTERVAL == 0:
            if not any(d['class'] == 1 for d in detections):
                if current_time - self.last_alarm_time['supervisor_missing'] >= self.alarm_interval:
                    alarms.append({
                        'type': 'supervisor_missing',
                        'distance': 0,
                        'message': 'WARNING: Supervisor not detected!'
                    })
                    self.last_alarm_time['supervisor_missing'] = current_time

        # 规则 5: 灭火器
        if self.frame_count % FIRE_EXTINGUISHER_CHECK_INTERVAL == 0:
            if not any(d['class'] == 3 for d in detections):
                if current_time - self.last_alarm_time['fire_extinguisher_missing'] >= self.alarm_interval:
                    alarms.append({
                        'type': 'fire_extinguisher_missing',
                        'distance': 0,
                        'message': 'WARNING: Fire extinguisher not detected!'
                    })
                    self.last_alarm_time['fire_extinguisher_missing'] = current_time

        # 规则 6: 违规工人
        if self.frame_count % WORKER_VIOLATION_CHECK_INTERVAL == 0:
            violation_boxes = [d for d in detections if d['class'] == 4]
            if len(violation_boxes) > 0:
                if current_time - self.last_alarm_time['worker_violation'] >= self.alarm_interval:
                    alarms.append({
                        'type': 'worker_violation',
                        'distance': 0,
                        'message': f'WARNING: Worker violation detected! ({len(violation_boxes)} person(s))'
                    })
                    self.last_alarm_time['worker_violation'] = current_time

        return alarms

    def _calc_distance(self, box1, box2):
        """计算两个检测框之间的三维距离（毫米）- 使用检测框中心坐标代表物体位置"""
        u1, v1 = box1['center']  # 使用中心坐标
        h1 = box1['height']
        u2, v2 = box2['center']  # 使用中心坐标
        h2 = box2['height']

        H1 = self.gas_heights.get(box1['class'], 1500)
        H2 = self.gas_heights.get(box2['class'], 1500)

        p1 = self.get_3d_point(u1, v1, h1, H1)
        p2 = self.get_3d_point(u2, v2, h2, H2)

        if p1 is None or p2 is None:
            return None

        return np.linalg.norm(p1 - p2) # NumPy中计算三维（及多维）空间两点间欧氏距离的常用API

    def _calc_distance_to_fire(self, box):
        """计算气瓶到动火点的三维距离（毫米）- 使用中心坐标"""
        u1, v1 = box['center']  # 使用中心坐标
        h1 = box['height']
        H1 = self.gas_heights.get(box['class'], 1500)

        p1 = self.get_3d_point(u1, v1, h1, H1)

        if p1 is None or self.fire_point is None:
            return None

        u2, v2 = self.fire_point
        p2 = self.get_3d_point(u2, v2, None, None)

        if p2 is None:
            return None

        return np.linalg.norm(p1 - p2)

    def draw_visualization(self, frame, detections, alarms, is_running=False):
        """
        绘制可视化信息

        参数：
        - frame: 视频帧
        - detections: 检测结果
        - alarms: 告警列表
        - is_running: 是否监控中
        """
        # 1. 绘制检测框（只在监控时显示）
        if is_running:
            for d in detections:
                box = d['box']
                cls_name = d['class_name']
                conf = d['confidence']

                # 根据类别设置颜色
                if d['class'] == 0:
                    color = (0, 255, 0)
                elif d['class'] == 1:
                    color = (128, 0, 128)
                elif d['class'] == 2:
                    color = (255, 0, 0)
                elif d['class'] == 3:
                    color = (0, 165, 255)
                elif d['class'] == 4:
                    color = (0, 0, 255)
                elif d['class'] == 5:
                    color = (42, 42, 165)
                elif d['class'] == 6:
                    color = (0, 255, 255)
                else:
                    color = (0, 255, 0)

                cv2.rectangle(frame, (int(box[0]), int(box[1])),
                            (int(box[2]), int(box[3])), color, 2)
                label = f"{cls_name} {conf:.2f}"
                cv2.putText(frame, label,
                        (int(box[0]), int(box[1])-5),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)

        # 2. 绘制连线（只在监控时显示）
        if is_running and self.fire_point:
            oxygen_boxes = [d for d in detections if d['class'] == 2]
            acetylene_boxes = [d for d in detections if d['class'] == 5]

            # 气瓶之间连线
            for o in oxygen_boxes:
                for a in acetylene_boxes:
                    center_o = (int(o['center'][0]), int(o['center'][1]))
                    center_a = (int(a['center'][0]), int(a['center'][1]))
                    dist = self._calc_distance(o, a)
                    if dist:
                        cv2.line(frame, center_o, center_a, (255, 0, 0), 2)
                        mid_point = ((center_o[0]+center_a[0])//2, (center_o[1]+center_a[1])//2)
                        cv2.putText(frame, f"{dist/1000:.2f}m", mid_point,
                                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 0, 0), 2)

            # 气瓶与动火点连线
            fire_point_int = (int(self.fire_point[0]), int(self.fire_point[1]))
            for b in oxygen_boxes + acetylene_boxes:
                center_b = (int(b['center'][0]), int(b['center'][1]))
                dist = self._calc_distance_to_fire(b)
                if dist:
                    cv2.line(frame, center_b, fire_point_int, (0, 255, 255), 2)
                    mid_point = ((center_b[0]+fire_point_int[0])//2,
                                (center_b[1]+fire_point_int[1])//2)
                    cv2.putText(frame, f"{dist/1000:.2f}m", mid_point,
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)

        # 3. 绘制告警信息
        y_offset = 30
        for alarm in alarms:
            cv2.putText(frame, alarm['message'], (10, y_offset),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
            y_offset += 30

        # 不绘制动火点标记（由前端 CSS 绘制，60+ FPS 对比后端抽帧绘制无明显视觉频闪）

        return frame

    def set_fire_point(self, x, y):
        """设置动火点坐标"""
        self.fire_point = (x, y)
        print("=" * 60)
        print("🎯 [FIRE_POINT] 动火点已设置")
        print(f"   坐标：({x:.2f}, {y:.2f})")
        print(f"   时间：{time.strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 60)

    def clear_fire_point(self):
        """清除动火点坐标"""
        self.fire_point = None
        print("=" * 60)
        print("🗑️ [ENGINE] 动火点已清除")
        print(f"   时间：{time.strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 60)

    def set_platform_height(self, height):
        """设置平台高度差（毫米）"""
        self.platform_height = height
        print(f"OK: Platform height set: {height}mm")
