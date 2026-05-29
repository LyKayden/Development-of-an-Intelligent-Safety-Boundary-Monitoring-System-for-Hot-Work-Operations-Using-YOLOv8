<template>
  <div class="app">
    <h1>🔥 动火作业智能监控系统</h1>

    <!-- 后端状态指示 -->
    <div class="backend-status" :class="getStatusClass()">
      <span v-if="backendOnline">🟢 后端服务已连接</span>
      <span v-else-if="isConnecting">🟡 正在连接后端服务...</span>
      <span v-else>🔴 后端服务未连接（请先启动后端）</span>
    </div>

    <!-- 操作密码验证弹窗 -->
    <div class="auth-overlay" v-if="requireAuth">
      <div class="auth-box">
        <h3>🔐 操作验证</h3>
        <p>{{ authOperation }}</p>
        <input
          type="password"
          v-model="authPassword"
          placeholder="请输入操作密码"
          @keyup.enter="verifyAuth"
          ref="passwordInput"
        />
        <div class="auth-buttons">
          <button @click="verifyAuth" class="btn-confirm">确认</button>
          <button @click="cancelAuth" class="btn-cancel">取消</button>
        </div>
        <p class="auth-hint">默认密码：123456</p>
        <p v-if="authError" class="auth-error">{{ authError }}</p>
      </div>
    </div>

    <!-- 控制面板 -->
    <div class="control-panel">
      <div class="input-row">
        <div class="input-group">
          <label>平台相对高度差 (米)：</label>
          <input
            type="number"
            v-model="platformHeight"
            step="0.1"
            placeholder="0"
            title="作业平台相对于气瓶中心点的高度差（平台高于气瓶填正值，低于填负值）"
          />
        </div>

        <div class="button-group">
          <button @click="requestStartTask" :disabled="isRunning || !backendOnline" class="btn-start">
            ▶ 开始监控
          </button>
          <button @click="requestStopTask" :disabled="!isRunning" class="btn-stop">
            ⏹ 停止监控
          </button>
          <button @click="requestClearFirePoint" :disabled="!firePoint || isRunning" class="btn-clear">
            🗑️ 清除动火点
          </button>
        </div>

        <div class="status">
          状态：<span :class="isRunning ? 'running' : 'stopped'">
            {{ isRunning ? '🟢 监控中' : '🔴 已停止' }}
          </span>
        </div>
      </div>
    </div>

    <!-- 视频流区域 -->
    <div class="video-wrapper">
      <div class="video-container" @click="handleVideoClick">
        <!-- 视频加载状态提示 -->
        <div class="video-loading" v-if="!videoLoaded">
          <div class="loading-spinner"></div>
          <p>📡 正在加载视频流...</p>
        </div>

        <!-- 播放 -->
        <img :src="videoUrl" ref="videoPlayer" @load="onVideoLoad" @error="onVideoError" style="display: block;" />

        <!-- 前端绘制动火点 -->
        <div v-if="firePoint" class="fire-point-marker"
            :style="{ left: firePoint.x + 'px', top: firePoint.y + 'px' }">
          <div class="marker-pin"></div>
          <div class="marker-label">Fire Point</div>
        </div>

        <!-- 后端未连接提示 -->
        <div class="video-overlay" v-if="!backendOnline && !isConnecting">
          <p>⚠️ 后端服务未启动</p>
          <p>请先运行 start.bat 或手动启动后端服务</p>
        </div>
      </div>
    </div>

    <!-- 告警面板 -->
    <div class="alarm-panel" v-if="hasActiveAlarms">
      <div class="alarm-header">
        <h2>⚠️ 当前告警</h2>
        <span class="alarm-count">{{ activeAlarms.length }} 条</span>
      </div>
      <div class="alarm-list">
        <div v-for="(alarm, index) in activeAlarms" :key="alarm.type + '-' + index"
            class="alarm-item"
            :class="getAlarmClass(alarm.type)">
          <span class="alarm-icon">{{ getAlarmIcon(alarm.type) }}</span>
          <span class="alarm-message">{{ alarm.message }}</span>
          <span class="alarm-distance" v-if="alarm.distance && alarm.distance > 0">
            {{ (alarm.distance / 1000).toFixed(2) }}m
          </span>
          <span class="alarm-time">{{ formatAlarmTime(alarm.timestamp) }}</span>
        </div>
      </div>
    </div>

    <!-- 无告警时显示提示 -->
    <div class="alarm-panel" v-else>
      <p style="text-align: center; color: #666; margin: 20px 0;">
        ✅ 暂无告警，一切正常
      </p>
    </div>

    <!-- 告警统计 -->
    <div class="stats-panel">
      <h3>📊 告警统计</h3>
      <div class="stats-grid">
        <div class="stat-item" :class="{ 'has-alert': stats.gas_to_gas > 0 }">
          <span class="stat-label">🔴 气瓶间距违规</span>
          <span class="stat-value">{{ stats.gas_to_gas }}</span>
        </div>
        <div class="stat-item" :class="{ 'has-alert': stats.gas_to_fire > 0 }">
          <span class="stat-label">🔴 气瓶 - 动火点违规</span>
          <span class="stat-value">{{ stats.gas_to_fire }}</span>
        </div>
        <div class="stat-item" :class="{ 'has-alert': stats.worker_violation > 0 }">
          <span class="stat-label">🔴 工人违规</span>
          <span class="stat-value">{{ stats.worker_violation }}</span>
        </div>
        <div class="stat-item" :class="{ 'has-alert': stats.safety_line_missing > 0 }">
          <span class="stat-label">🟡 警戒线缺失</span>
          <span class="stat-value">{{ stats.safety_line_missing }}</span>
        </div>
        <div class="stat-item" :class="{ 'has-alert': stats.supervisor_missing > 0 }">
          <span class="stat-label">🟡 监护人缺失</span>
          <span class="stat-value">{{ stats.supervisor_missing }}</span>
        </div>
        <div class="stat-item" :class="{ 'has-alert': stats.fire_extinguisher_missing > 0 }">
          <span class="stat-label">🟡 灭火器缺失</span>
          <span class="stat-value">{{ stats.fire_extinguisher_missing }}</span>
        </div>
      </div>
      <button @click="requestResetStats" class="btn-reset" v-if="hasAnyStats">
        🔄 重置统计
      </button>
    </div>

    <!-- 操作说明 -->
    <div class="help">
      <h3>📖 使用说明</h3>
      <ol>
        <li>双击 start.bat 启动系统</li>
        <li>等待视频流加载完成</li>
        <li>输入平台相对高度差（米）：测量作业平台相对于气瓶中心点的高度差，平台高于气瓶填正值，低于填负值</li>
        <li>点击视频画面中动火点位置进行锚定</li>
        <li>点击"开始监控"按钮</li>
        <li>系统自动检测气瓶并计算距离</li>
      </ol>

      <h4>🛡️ 动火作业安全规则（GB 30871-2022）</h4>
      <ul>
        <li><span class="rule-distance">氧气瓶与乙炔瓶间距 ≥ 5 米</span></li>
        <li><span class="rule-distance">气瓶与动火点间距 ≥ 10 米</span></li>
        <li><span class="rule-required">警戒线必须设置</span></li>
        <li><span class="rule-required">监护人必须在岗</span></li>
        <li><span class="rule-required">灭火器必须配备</span></li>
        <li><span class="rule-violation">工人违规行为自动检测</span></li>
      </ul>
    </div>
  </div>
</template>

<script>
import { io } from 'socket.io-client';
import axios from 'axios';

export default {
  name: 'App',
  data() {
    // 新增：获取当前主机地址
    const host = window.location.hostname;
    const baseURL = `${window.location.protocol}//${host}:5000`;

    return {
      // 修改：自动获取当前主机地址
      baseURL: baseURL,  // 新增：基础 URL
      videoUrl: `${baseURL}/video`,  // 修改：使用 baseURL
      isRunning: false,
      firePoint: null,
      platformHeight: 0,
      activeAlarms: [],
      alarmHistory: [],
      socket: null,
      backendOnline: false,
      isConnecting: false,
      videoLoaded: false,
      stats: {
        gas_to_gas: 0,
        gas_to_fire: 0,
        worker_violation: 0,
        safety_line_missing: 0,
        supervisor_missing: 0,
        fire_extinguisher_missing: 0
      },
      reconnectAttempts: 0,
      isAudioPlaying: false,
      criticalAlarmTypes: [
        'gas_to_gas',
        'gas_to_fire',
        'worker_violation'
      ],

      // 认证相关数据
      requireAuth: false,  // 是否需要认证
      authOperation: '',   // 当前操作名称
      authPassword: '',    // 输入的密码
      authError: '',       // 待执行的动作名称
      pendingAction: null  // 临时存储待执行的动作名称
    };
  },
  computed: {
    hasActiveAlarms() {
      return this.activeAlarms.length > 0;
    },
    hasAnyStats() {
      return Object.values(this.stats).some(v => v > 0);
    }
  },
  mounted() {
    this.connectWebSocket();
    setInterval(this.fetchStats, 5000);
  },
  methods: {
    connectWebSocket() {
      this.isConnecting = true;

      // 新增：自动获取当前主机地址
      this.socket = io(this.baseURL, {
        reconnection: true,
        reconnectionDelay: 1000,
        reconnectionAttempts: 10
      });

      this.socket.on('connect', () => {
        this.backendOnline = true;
        this.isConnecting = false;
        this.reconnectAttempts = 0;
        console.log('✅ 后端服务已连接');
      });

      this.socket.on('disconnect', () => {
        this.backendOnline = false;
        this.isConnecting = false;
        console.log('❌ 后端服务已断开');
      });

      this.socket.on('alarm', (data) => {
        this.handleAlarm(data);
      });

      this.socket.on('connect_error', (error) => {
        console.log('连接错误:', error);
        this.reconnectAttempts++;
        if (this.reconnectAttempts >= 10) {
          this.isConnecting = false;
          alert('⚠️ 无法连接到后端服务，请检查后端是否运行！');
        }
      });
    },

    getStatusClass() {
      if (this.backendOnline) return 'online';
      if (this.isConnecting) return 'connecting';
      return 'offline';
    },

    // 修复：处理视频点击（立即计算坐标）
    handleVideoClick(event) {
      if (!this.backendOnline) {
        alert('后端服务未启动，请先启动后端服务！');
        return;
      }
      if (this.isRunning) {
        alert('监控中无法修改动火点，请先停止监控！');
        return;
      }

      // 立即计算坐标（不等到认证后）
      const rect = event.currentTarget.getBoundingClientRect();
      const clickX = event.clientX - rect.left;
      const clickY = event.clientY - rect.top;

      // 存储坐标到临时变量
      this.tempFirePoint = { x: clickX, y: clickY };

      // 触发认证
      this.authOperation = '锚定动火点';
      this.pendingAction = 'setFirePoint';
      this.showAuthDialog();
    },

    // 显示认证对话框
    showAuthDialog() {
      this.requireAuth = true;
      this.authPassword = '';
      this.authError = '';

      this.$nextTick(() => {
        if (this.$refs.passwordInput) {
          this.$refs.passwordInput.focus();
        }
      });
    },

    // 修复：验证密码
    verifyAuth() {
      if (this.authPassword === '123456') {
        console.log('✅ 密码验证通过');

        // 先关闭对话框
        this.requireAuth = false;
        this.authPassword = '';
        this.authError = '';

        // 根据动作名称执行对应操作
        if (this.pendingAction === 'setFirePoint') {
          this.executeSetFirePoint();
        } else if (this.pendingAction === 'startTask') {
          this.doStartTask();
        } else if (this.pendingAction === 'stopTask') {
          this.doStopTask();
        } else if (this.pendingAction === 'clearFirePoint') {
          this.doClearFirePoint();
        } else if (this.pendingAction === 'resetStats') {
          this.doResetStats();
        }

        // 清空动作
        this.pendingAction = null;
        this.tempFirePoint = null;
      } else {
        this.authError = '❌ 密码错误！';
        this.authPassword = '';
      }
    },

    // 新增：执行设置动火点（使用临时坐标）
    executeSetFirePoint() {
      if (!this.tempFirePoint) {
        console.error('❌ 临时坐标丢失');
        return;
      }

      this.firePoint = { ...this.tempFirePoint };

      console.log("=".repeat(60));
      console.log("🖱️ [FRONTEND] 用户点击视频画面");
      console.log(`   点击坐标：(${this.firePoint.x.toFixed(2)}, ${this.firePoint.y.toFixed(2)})`);

      axios.post(`${this.baseURL}/set_fire_point`, {
        x: this.firePoint.x,
        y: this.firePoint.y
      }, { timeout: 5000 })
        .then(response => {
          if (response.data.status === 'success') {
            console.log("✅ 动火点设置成功");
          }
        })
        .catch(error => {
          console.error('❌ 设置动火点失败:', error);
          alert('无法连接到后端服务');
        });
    },

    cancelAuth() {
      this.requireAuth = false;
      this.authPassword = '';
      this.authError = '';
      this.pendingAction = null;
      this.tempFirePoint = null;
      console.log('❌ 操作已取消');
    },

    // 修复：请求启动监控
    requestStartTask() {
      if (!this.backendOnline) {
        alert('后端服务未连接，请先启动后端服务！');
        return;
      }
      if (!this.firePoint) {
        alert('请先点击视频画面锚定动火点！');
        return;
      }

      this.authOperation = '启动监控';
      this.pendingAction = 'startTask';
      this.showAuthDialog();
    },

    requestStopTask() {
      this.authOperation = '停止监控';
      this.pendingAction = 'stopTask';
      this.showAuthDialog();
    },

    requestClearFirePoint() {
      this.authOperation = '清除动火点';
      this.pendingAction = 'clearFirePoint';
      this.showAuthDialog();
    },

    requestResetStats() {
      this.authOperation = '重置统计';
      this.pendingAction = 'resetStats';
      this.showAuthDialog();
    },

    doStartTask() {
      axios.post(`${this.baseURL}/start`, {
        fire_point_x: this.firePoint.x,
        fire_point_y: this.firePoint.y,
        platform_height: this.platformHeight * 1000
      }, { timeout: 5000 })
        .then(response => {
          if (response.data.status === 'started') {
            this.isRunning = true;
            console.log('✅ 监控已启动');
          }
        })
        .catch(error => {
          console.error('❌ 启动失败:', error);
          alert('启动失败');
        });
    },

    doStopTask() {
      axios.post(`${this.baseURL}/stop`, { timeout: 5000 })
        .then(response => {
          if (response.data.status === 'stopped') {
            this.isRunning = false;
            this.activeAlarms = [];
            console.log('⏹ 监控已停止');
          }
        })
        .catch(error => {
          console.error('❌ 停止失败:', error);
        });
    },

    doClearFirePoint() {
      this.firePoint = null;
      axios.post(`${this.baseURL}/clear_fire_point`)
        .then(response => {
          if (response.data.status === 'success') {
            console.log('✅ 动火点已清除');
          }
        })
        .catch(error => {
          console.error('❌ 清除失败:', error);
        });
    },

    doResetStats() {
      axios.post(`${this.baseURL}/reset_stats`)
        .then(() => {
          this.stats = {
            gas_to_gas: 0,
            gas_to_fire: 0,
            worker_violation: 0,
            safety_line_missing: 0,
            supervisor_missing: 0,
            fire_extinguisher_missing: 0
          };
          console.log('🔄 统计已重置');
        })
        .catch(error => {
          console.error('❌ 重置失败:', error);
        });
    },

    getAlarmClass(type) {
      const classMap = {
        'gas_to_gas': 'alarm-critical',
        'gas_to_fire': 'alarm-critical',
        'worker_violation': 'alarm-critical',
        'safety_line_missing': 'alarm-warning',
        'supervisor_missing': 'alarm-warning',
        'fire_extinguisher_missing': 'alarm-warning'
      };
      return classMap[type] || '';
    },

    getAlarmIcon(type) {
      const iconMap = {
        'gas_to_gas': '🔴',
        'gas_to_fire': '🔴',
        'worker_violation': '🔴',
        'safety_line_missing': '🟡',
        'supervisor_missing': '🟡',
        'fire_extinguisher_missing': '🟡'
      };
      return iconMap[type] || '⚠️';
    },

    formatAlarmTime(timestamp) {
      if (!timestamp) return '';
      const diff = Date.now() - timestamp;
      const seconds = Math.floor(diff / 1000);
      if (seconds < 60) return `${seconds}秒前`;
      const minutes = Math.floor(seconds / 60);
      if (minutes < 60) return `${minutes}分钟前`;
      const hours = Math.floor(minutes / 60);
      return `${hours}小时前`;
    },

    handleAlarm(data) {
      data.timestamp = Date.now();
      const existingIndex = this.activeAlarms.findIndex(a => a.type === data.type);
      if (existingIndex > -1) {
        this.activeAlarms[existingIndex] = data;
      } else {
        this.activeAlarms.push(data);
        this.playAlarmSound(data.type);
      }
      this.alarmHistory.push({ ...data, timestamp: Date.now() });
      const duration = (data.type === 'gas_to_gas' || data.type === 'gas_to_fire' || data.type === 'worker_violation') ? 10000 : 8000;
      setTimeout(() => {
        const index = this.activeAlarms.findIndex(a => a.type === data.type);
        if (index > -1) this.activeAlarms.splice(index, 1);
      }, duration);
    },

    playAlarmSound(alarmType) {
      // 只播放紧急告警音频
      if (!this.criticalAlarmTypes.includes(alarmType)) return;
      if (this.isAudioPlaying) return;
      const alarmAudio = new Audio('/audio/alarm.mp3');
      alarmAudio.volume = 0.5;
      this.isAudioPlaying = true;
      alarmAudio.play().catch(e => console.warn('音频播放失败:', e.message));
      alarmAudio.onended = () => { this.isAudioPlaying = false; };
      alarmAudio.onerror = () => { this.isAudioPlaying = false; };
    },

    async fetchStats() {
      try {
        const response = await axios.get(`${this.baseURL}/stats`);
        this.stats = response.data;
      } catch (error) {
        console.error('获取统计失败:', error);
      }
    },

    onVideoLoad() {
      this.videoLoaded = true;
      console.log('✅ 视频流已加载');
    },

    onVideoError() {
      this.videoLoaded = false;
      console.log('❌ 视频流加载失败');
    }
  },
  beforeUnmount() {
    if (this.socket) this.socket.disconnect();
  }
};
</script>

<style scoped>
.app {
  font-family: 'Microsoft YaHei', Arial, sans-serif;
  max-width: 1400px;
  margin: 0 auto;
  padding: 20px;
  background: #f5f7fa;
  min-height: 100vh;
}

h1 {
  text-align: center;
  color: #2c3e50;
  margin-bottom: 20px;
  font-size: 32px;
}

.backend-status {
  text-align: center;
  padding: 10px;
  border-radius: 5px;
  margin-bottom: 20px;
  font-weight: bold;
}

.backend-status.online {
  background: #d4edda;
  color: #155724;
}

.backend-status.offline {
  background: #f8d7da;
  color: #721c24;
}

.backend-status.connecting {
  background: #fff3cd;
  color: #856404;
}

.auth-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.7);
  z-index: 1000;
  display: flex;
  align-items: center;
  justify-content: center;
}

.auth-box {
  background: white;
  padding: 30px;
  border-radius: 10px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
  text-align: center;
  min-width: 320px;
}

.auth-box h3 {
  margin: 0 0 15px 0;
  color: #2c3e50;
  font-size: 20px;
}

.auth-box p {
  margin: 10px 0;
  color: #666;
  font-size: 14px;
}

.auth-box input {
  width: 100%;
  padding: 12px;
  border: 2px solid #ddd;
  border-radius: 5px;
  font-size: 16px;
  margin: 15px 0;
  box-sizing: border-box;
}

.auth-box input:focus {
  border-color: #42b983;
  outline: none;
}

.auth-buttons {
  display: flex;
  gap: 10px;
  justify-content: center;
  margin-top: 15px;
}

.auth-buttons button {
  padding: 10px 25px;
  border: none;
  border-radius: 5px;
  cursor: pointer;
  font-size: 14px;
  font-weight: bold;
}

.btn-confirm {
  background: #42b983;
  color: white;
}

.btn-confirm:hover {
  background: #369970;
}

.btn-cancel {
  background: #e74c3c;
  color: white;
}

.btn-cancel:hover {
  background: #c0392b;
}

.auth-hint {
  font-size: 12px;
  color: #999;
  margin-top: 15px;
}

.auth-error {
  color: #e74c3c;
  font-size: 14px;
  margin-top: 10px;
  font-weight: bold;
}

.video-loading {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.8);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  color: white;
  z-index: 20;
}

.loading-spinner {
  width: 50px;
  height: 50px;
  border: 4px solid #f3f3f3;
  border-top: 4px solid #42b983;
  border-radius: 50%;
  animation: spin 1s linear infinite;
  margin-bottom: 15px;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

.control-panel {
  background: white;
  padding: 20px;
  border-radius: 10px;
  box-shadow: 0 2px 12px rgba(0,0,0,0.1);
  margin-bottom: 20px;
}

.input-row {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 30px;
  flex-wrap: wrap;
}

.input-group {
  display: flex;
  align-items: center;
  gap: 10px;
}

.input-group label {
  font-weight: bold;
  font-size: 16px;
}

.input-group input {
  padding: 10px 15px;
  border: 1px solid #ddd;
  border-radius: 5px;
  width: 120px;
  font-size: 16px;
}

.button-group {
  display: flex;
  gap: 15px;
}

button {
  padding: 12px 30px;
  border: none;
  border-radius: 5px;
  cursor: pointer;
  font-size: 16px;
  font-weight: bold;
  transition: all 0.3s;
}

button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn-start {
  background: #42b983;
  color: white;
}

.btn-start:hover:not(:disabled) {
  background: #369970;
}

.btn-stop {
  background: #e74c3c;
  color: white;
}

.btn-stop:hover:not(:disabled) {
  background: #c0392b;
}

.btn-reset {
  background: #6c757d;
  color: white;
  margin-top: 15px;
  padding: 8px 20px;
  font-size: 14px;
}

.btn-reset:hover {
  background: #5a6268;
}

.btn-clear {
  background: #6c757d;
  color: white;
}

.btn-clear:hover:not(:disabled) {
  background: #5a6268;
}

.status {
  font-size: 18px;
  font-weight: bold;
}

.running {
  color: #42b983;
}

.stopped {
  color: #999;
}

.video-wrapper {
  margin: 20px auto;
  max-width: 1280px;
}

.video-container {
  position: relative;
  width: 100%;
  aspect-ratio: 16/9;
  border: 4px solid #333;
  border-radius: 10px;
  overflow: hidden;
  cursor: crosshair;
  background: #000;
  box-shadow: 0 4px 20px rgba(0,0,0,0.3);
}

.video-container img {
  width: 100%;
  height: 100%;
  object-fit: contain;
  display: block;
}

.fire-point-marker {
  position: absolute;
  transform: translate(-50%, -100%);
  z-index: 10;
  pointer-events: none;
  animation: none;
}

.marker-pin {
  width: 24px;
  height: 24px;
  background: #ff4444;
  border: 3px solid white;
  border-radius: 50% 50% 50% 0;
  transform: rotate(-45deg);
  box-shadow: 0 2px 10px rgba(0,0,0,0.5);
}

.marker-label {
  position: absolute;
  top: -25px;
  left: 50%;
  transform: translateX(-50%);
  background: rgba(0, 0, 0, 0.8);
  color: white;
  padding: 3px 8px;
  border-radius: 3px;
  font-size: 12px;
  font-weight: bold;
  white-space: nowrap;
}

.video-overlay {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  color: white;
  font-size: 20px;
  text-align: center;
  background: rgba(0,0,0,0.8);
  padding: 30px;
  border-radius: 10px;
  z-index: 5;
}

.video-overlay p {
  margin: 10px 0;
}

.alarm-panel {
  margin-top: 20px;
  padding: 20px;
  background: #ffe6e6;
  border: 3px solid #ff0000;
  border-radius: 10px;
  animation: slideDown 0.3s ease;
}

@keyframes slideDown {
  from {
    opacity: 0;
    transform: translateY(-20px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.alarm-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 15px;
}

.alarm-header h2 {
  color: #ff0000;
  margin: 0;
}

.alarm-count {
  background: #ff0000;
  color: white;
  padding: 5px 15px;
  border-radius: 20px;
  font-size: 14px;
  font-weight: bold;
}

.alarm-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.alarm-item {
  padding: 15px;
  background: white;
  border-radius: 5px;
  display: flex;
  align-items: center;
  gap: 15px;
  animation: slideIn 0.3s ease;
  box-shadow: 0 2px 5px rgba(0,0,0,0.1);
}

@keyframes slideIn {
  from {
    opacity: 0;
    transform: translateX(-20px);
  }
  to {
    opacity: 1;
    transform: translateX(0);
  }
}

.alarm-critical {
  border-left: 5px solid #ff0000;
}

.alarm-warning {
  border-left: 5px solid #ff9800;
}

.alarm-icon {
  font-size: 28px;
}

.alarm-message {
  flex: 1;
  font-weight: bold;
  font-size: 16px;
  color: #333;
}

.alarm-critical .alarm-message {
  color: #ff0000;
}

.alarm-warning .alarm-message {
  color: #e65100;
}

.alarm-distance {
  font-size: 18px;
  font-weight: bold;
  color: #666;
  background: #f5f5f5;
  padding: 5px 10px;
  border-radius: 5px;
}

.alarm-time {
  font-size: 12px;
  color: #999;
}

.stats-panel {
  margin-top: 20px;
  background: white;
  padding: 20px;
  border-radius: 10px;
  box-shadow: 0 2px 12px rgba(0,0,0,0.1);
}

.stats-panel h3 {
  color: #2c3e50;
  margin-top: 0;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 15px;
  margin-top: 15px;
}

.stat-item {
  background: #f5f7fa;
  padding: 15px;
  border-radius: 5px;
  text-align: center;
  transition: all 0.3s;
}

.stat-item.has-alert {
  background: #fff3cd;
  border: 2px solid #ffc107;
  animation: pulse-alert 2s infinite;
}

@keyframes pulse-alert {
  0%, 100% {
    box-shadow: 0 0 0 0 rgba(255, 193, 7, 0.4);
  }
  50% {
    box-shadow: 0 0 0 10px rgba(255, 193, 7, 0);
  }
}

.stat-label {
  display: block;
  font-size: 14px;
  color: #666;
  margin-bottom: 10px;
}

.stat-value {
  display: block;
  font-size: 32px;
  font-weight: bold;
  color: #2c3e50;
}

.stat-item.has-alert .stat-value {
  color: #e74c3c;
}

.help {
  margin-top: 30px;
  background: white;
  padding: 20px;
  border-radius: 10px;
  box-shadow: 0 2px 12px rgba(0,0,0,0.1);
}

.help h3 {
  color: #2c3e50;
  margin-top: 0;
}

.help h4 {
  color: #2c3e50;
  margin-top: 20px;
}

.help ol, .help ul {
  line-height: 2;
  color: #555;
  font-size: 16px;
}

.rule-distance {
  color: #e74c3c;
  font-weight: bold;
}

.rule-required {
  color: #ff9800;
  font-weight: bold;
}

.rule-violation {
  color: #ff0000;
  font-weight: bold;
}
</style>
