import streamlit as st
import paho.mqtt.client as mqtt
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
import json
import time
import logging
import threading
import random

# 配置日誌
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class MQTTManager:
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(MQTTManager, cls).__new__(cls)
                cls._instance._initialized = False
            return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
            
        self._initialized = True
        self.connected = False
        self.data_buffer = {
            "pressure": [],
            "vibration": [],
            "rpm": [],
            "current": []
        }
        self.sn_buffer = {
            "pressure": [],
            "vibration": [],
            "rpm": [],
            "current": []
        }
        self.client = None
        self._setup_mqtt()
    
    def _setup_mqtt(self):
        self.client = mqtt.Client()
        self.client.username_pw_set("jetsion", "jetsion")
        self.client.on_connect = self._on_connect
        self.client.on_disconnect = self._on_disconnect
        self.client.on_message = self._on_message
        
        try:
            self.client.connect("jetsion.com", 1883, 60)
            self.client.loop_start()
            logger.info("MQTT 連接請求已發送")
        except Exception as e:
            logger.error(f"MQTT 連接失敗: {str(e)}")
    
    def _on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            self.connected = True
            # 訂閱所有相關主題
            client.subscribe("jetsion/taguchi/device001/#")
            logger.info("已成功訂閱主題 jetsion/taguchi/device001/#")
        else:
            self.connected = False
            logger.error(f"連接失敗，返回碼: {rc}")
    
    def _on_disconnect(self, client, userdata, rc):
        self.connected = False
        logger.warning("與 MQTT broker 斷開連接")
    
    def _on_message(self, client, userdata, msg):
        try:
            topic = msg.topic
            payload = msg.payload.decode()
            timestamp = datetime.now()
            
            logger.info(f"收到消息 - Topic: {topic}, Payload: {payload}")
            
            # 解析主題
            parts = topic.split("/")
            if len(parts) >= 4:
                sensor_type = parts[-1]  # 最後一個部分是感測器類型
                
                # 處理 S/N 比數據
                if "sn_ratio" in topic:
                    try:
                        value = float(payload)
                        if sensor_type not in self.sn_buffer:
                            self.sn_buffer[sensor_type] = []
                        
                        self.sn_buffer[sensor_type].append({
                            "timestamp": timestamp,
                            "value": value
                        })
                        
                        if len(self.sn_buffer[sensor_type]) > 100:
                            self.sn_buffer[sensor_type] = self.sn_buffer[sensor_type][-100:]
                        
                        logger.info(f"更新 {sensor_type} S/N 比數據: {value}")
                    except ValueError:
                        logger.error(f"S/N 比數據格式錯誤: {payload}")
                
                # 處理原始感測器數據
                elif sensor_type in ["pressure", "vibration", "rpm", "current"]:
                    try:
                        value = float(payload)
                        if sensor_type not in self.data_buffer:
                            self.data_buffer[sensor_type] = []
                        
                        self.data_buffer[sensor_type].append({
                            "timestamp": timestamp,
                            "value": value
                        })
                        
                        if len(self.data_buffer[sensor_type]) > 100:
                            self.data_buffer[sensor_type] = self.data_buffer[sensor_type][-100:]
                        
                        logger.info(f"更新 {sensor_type} 原始數據: {value}")
                        logger.info(f"當前 {sensor_type} 緩衝區大小: {len(self.data_buffer[sensor_type])}")
                    except ValueError:
                        logger.error(f"原始數據格式錯誤: {payload}")
                
        except Exception as e:
            logger.error(f"處理數據失敗: {str(e)}")
    
    def get_data(self):
        return self.data_buffer
    
    def get_sn_data(self):
        return self.sn_buffer
    
    def is_connected(self):
        return self.connected

class TaguchiUI:
    def __init__(self):
        # 控制因子數據
        self.control_factors = {
            "A": {"1": 25, "2": 30, "3": 35},  # 壓力
            "B": {"1": 1000, "2": 2000, "3": 3000},  # 轉速
            "C": {"1": 5, "2": 10, "3": 15}  # 電流
        }
        
        # 初始化 MQTT 管理器
        if 'mqtt_manager' not in st.session_state:
            st.session_state.mqtt_manager = MQTTManager()
        
        # 初始化實驗設定
        if 'experiment_settings' not in st.session_state:
            st.session_state.experiment_settings = {
                'current_factor': 'A',
                'current_level': '1',
                'experiment_running': False,
                'level_history': {
                    'A': {'1': [], '2': [], '3': []},
                    'B': {'1': [], '2': [], '3': []},
                    'C': {'1': [], '2': [], '3': []}
                }
            }
    
    def generate_sensor_data(self, factor, level):
        """根據控制因子設定生成模擬感測器數據"""
        base_value = self.control_factors[factor][level]
        noise = random.uniform(-0.1, 0.1) * base_value
        
        if factor == 'A':  # 溫度
            return {
                'pressure': base_value + noise,
                'vibration': base_value * 0.5 + random.uniform(-2, 2),
                'rpm': base_value * 20 + random.uniform(-50, 50),
                'current': base_value * 0.8 + random.uniform(-3, 3)
            }
        elif factor == 'B':  # 壓力
            return {
                'pressure': base_value * 0.3 + random.uniform(-5, 5),
                'vibration': base_value + noise,
                'rpm': base_value * 15 + random.uniform(-30, 30),
                'current': base_value * 0.6 + random.uniform(-4, 4)
            }
        else:  # 轉速
            return {
                'pressure': base_value * 0.01 + random.uniform(-1, 1),
                'vibration': base_value * 0.02 + random.uniform(-2, 2),
                'rpm': base_value + noise,
                'current': base_value * 0.4 + random.uniform(-20, 20)
            }
        logger.info(f"生成感測器數據 - 因子: {factor}, 水準: {level}, 數據: {data}")
    
    def run(self):
        """運行UI"""
        st.set_page_config(page_title="田口法實驗監控系統", layout="wide")
        
        st.title("田口法實驗監控系統")
        
        # 顯示連接狀態
        if st.session_state.mqtt_manager.is_connected():
            st.success("已連接到 MQTT broker")
        else:
            st.warning("未連接到 MQTT broker，使用本地模式")
        
        # 感測器數據顯示
        st.header("感測器數據")
        data = st.session_state.mqtt_manager.get_data()
        sn_data = st.session_state.mqtt_manager.get_sn_data()
        
        # 顯示數據緩存狀態
        st.write("數據緩存狀態：")
        st.write("原始值數據：", {k: len(v) for k, v in data.items()})
        st.write("S/N 比值數據：", {k: len(v) for k, v in sn_data.items()})
        
        # 壓力數據
        st.subheader("壓力數據")
        col1, col2 = st.columns(2)
        with col1:
            if data["pressure"]:
                df = pd.DataFrame(data["pressure"])
                fig = go.Figure()
                fig.add_trace(go.Scatter(
                    x=df["timestamp"],
                    y=df["value"],
                    name="壓力原始值",
                    line=dict(color='blue')
                ))
                fig.update_layout(
                    title="壓力原始值趨勢圖",
                    xaxis_title="時間",
                    yaxis_title="數值"
                )
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.warning("尚未收到壓力原始值數據")
        
        with col2:
            if sn_data["pressure"]:
                df_sn = pd.DataFrame(sn_data["pressure"])
                fig = go.Figure()
                fig.add_trace(go.Scatter(
                    x=df_sn["timestamp"],
                    y=df_sn["value"],
                    name="壓力 S/N 比",
                    line=dict(color='blue')
                ))
                fig.update_layout(
                    title="壓力 S/N 比趨勢圖",
                    xaxis_title="時間",
                    yaxis_title="S/N 比 (dB)"
                )
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.warning("尚未收到壓力 S/N 比值數據")
        
        # 振動數據
        st.subheader("振動數據")
        col1, col2 = st.columns(2)
        with col1:
            if data["vibration"]:
                df = pd.DataFrame(data["vibration"])
                fig = go.Figure()
                fig.add_trace(go.Scatter(
                    x=df["timestamp"],
                    y=df["value"],
                    name="振動原始值",
                    line=dict(color='red')
                ))
                fig.update_layout(
                    title="振動原始值趨勢圖",
                    xaxis_title="時間",
                    yaxis_title="數值"
                )
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.warning("尚未收到振動原始值數據")
        
        with col2:
            if sn_data["vibration"]:
                df_sn = pd.DataFrame(sn_data["vibration"])
                fig = go.Figure()
                fig.add_trace(go.Scatter(
                    x=df_sn["timestamp"],
                    y=df_sn["value"],
                    name="振動 S/N 比",
                    line=dict(color='red')
                ))
                fig.update_layout(
                    title="振動 S/N 比趨勢圖",
                    xaxis_title="時間",
                    yaxis_title="S/N 比 (dB)"
                )
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.warning("尚未收到振動 S/N 比值數據")
        
        # 轉速數據
        st.subheader("轉速數據")
        col1, col2 = st.columns(2)
        with col1:
            if data["rpm"]:
                df = pd.DataFrame(data["rpm"])
                fig = go.Figure()
                fig.add_trace(go.Scatter(
                    x=df["timestamp"],
                    y=df["value"],
                    name="轉速原始值",
                    line=dict(color='green')
                ))
                fig.update_layout(
                    title="轉速原始值趨勢圖",
                    xaxis_title="時間",
                    yaxis_title="數值"
                )
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.warning("尚未收到轉速原始值數據")
        
        with col2:
            if sn_data["rpm"]:
                df_sn = pd.DataFrame(sn_data["rpm"])
                fig = go.Figure()
                fig.add_trace(go.Scatter(
                    x=df_sn["timestamp"],
                    y=df_sn["value"],
                    name="轉速 S/N 比",
                    line=dict(color='green')
                ))
                fig.update_layout(
                    title="轉速 S/N 比趨勢圖",
                    xaxis_title="時間",
                    yaxis_title="S/N 比 (dB)"
                )
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.warning("尚未收到轉速 S/N 比值數據")
        
        # 電流數據
        st.subheader("電流數據")
        col1, col2 = st.columns(2)
        with col1:
            if data["current"]:
                df = pd.DataFrame(data["current"])
                fig = go.Figure()
                fig.add_trace(go.Scatter(
                    x=df["timestamp"],
                    y=df["value"],
                    name="電流原始值",
                    line=dict(color='purple')
                ))
                fig.update_layout(
                    title="電流原始值趨勢圖",
                    xaxis_title="時間",
                    yaxis_title="數值"
                )
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.warning("尚未收到電流原始值數據")
        
        with col2:
            if sn_data["current"]:
                df_sn = pd.DataFrame(sn_data["current"])
                fig = go.Figure()
                fig.add_trace(go.Scatter(
                    x=df_sn["timestamp"],
                    y=df_sn["value"],
                    name="電流 S/N 比",
                    line=dict(color='purple')
                ))
                fig.update_layout(
                    title="電流 S/N 比趨勢圖",
                    xaxis_title="時間",
                    yaxis_title="S/N 比 (dB)"
                )
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.warning("尚未收到電流 S/N 比值數據")
        
        # 控制因子設定
        st.header("控制因子設定")
        
        # 創建三列用於顯示控制因子
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.subheader("因子 A (壓力)")
            st.write("水準 1: 25 bar")
            st.write("水準 2: 30 bar")
            st.write("水準 3: 35 bar")
            
            # 添加水準選擇器
            level_a = st.selectbox("選擇水準", ["1", "2", "3"], key="level_a")
            
            if st.button("設定因子 A"):
                st.session_state.experiment_settings['current_factor'] = 'A'
                st.session_state.experiment_settings['experiment_running'] = True
                # 根據選擇的水準發布對應的值
                level_values = {"1": "25", "2": "30", "3": "35"}
                st.session_state.mqtt_manager.client.publish(
                    "jetsion/taguchi/device001/control_factors/A",
                    level_values[level_a]
                )
                # 收集當前數據到 level_history
                current_data = st.session_state.mqtt_manager.get_data()
                if current_data:
                    logger.info(f"收集因子 A 水準 {level_a} 的數據: {current_data}")
                    formatted_data = {}
                    for sensor_type, measurements in current_data.items():
                        if measurements:
                            formatted_data[sensor_type] = measurements[-1]
                    st.session_state.experiment_settings['level_history']['A'][level_a].append(formatted_data)
        
        with col2:
            st.subheader("因子 B (轉速)")
            st.write("水準 1: 1000 RPM")
            st.write("水準 2: 2000 RPM")
            st.write("水準 3: 3000 RPM")
            
            # 添加水準選擇器
            level_b = st.selectbox("選擇水準", ["1", "2", "3"], key="level_b")
            
            if st.button("設定因子 B"):
                st.session_state.experiment_settings['current_factor'] = 'B'
                st.session_state.experiment_settings['experiment_running'] = True
                # 根據選擇的水準發布對應的值
                level_values = {"1": "1000", "2": "2000", "3": "3000"}
                st.session_state.mqtt_manager.client.publish(
                    "jetsion/taguchi/device001/control_factors/B",
                    level_values[level_b]
                )
                # 收集當前數據到 level_history
                current_data = st.session_state.mqtt_manager.get_data()
                if current_data:
                    logger.info(f"收集因子 B 水準 {level_b} 的數據: {current_data}")
                    formatted_data = {}
                    for sensor_type, measurements in current_data.items():
                        if measurements:
                            formatted_data[sensor_type] = measurements[-1]
                    st.session_state.experiment_settings['level_history']['B'][level_b].append(formatted_data)
        
        with col3:
            st.subheader("因子 C (電流)")
            st.write("水準 1: 5 A")
            st.write("水準 2: 10 A")
            st.write("水準 3: 15 A")
            
            # 添加水準選擇器
            level_c = st.selectbox("選擇水準", ["1", "2", "3"], key="level_c")
            
            if st.button("設定因子 C"):
                st.session_state.experiment_settings['current_factor'] = 'C'
                st.session_state.experiment_settings['experiment_running'] = True
                # 根據選擇的水準發布對應的值
                level_values = {"1": "5", "2": "10", "3": "15"}
                st.session_state.mqtt_manager.client.publish(
                    "jetsion/taguchi/device001/control_factors/C",
                    level_values[level_c]
                )
                # 收集當前數據到 level_history
                current_data = st.session_state.mqtt_manager.get_data()
                if current_data:
                    logger.info(f"收集因子 C 水準 {level_c} 的數據: {current_data}")
                    formatted_data = {}
                    for sensor_type, measurements in current_data.items():
                        if measurements:
                            formatted_data[sensor_type] = measurements[-1]
                    st.session_state.experiment_settings['level_history']['C'][level_c].append(formatted_data)
        
        # 顯示當前實驗狀態
        st.subheader("當前實驗狀態")
        if st.session_state.experiment_settings['experiment_running']:
            current_factor = st.session_state.experiment_settings['current_factor']
            st.info(f"正在進行因子 {current_factor} 的實驗")
            
            # 顯示當前因子的設定值
            factor_values = self.control_factors[current_factor]
            st.write(f"當前因子 {current_factor} 的設定值：")
            for level, value in factor_values.items():
                st.write(f"水準 {level}: {value}")
            
            # 顯示各水準的數據比較
            st.subheader("各水準數據比較")
            level_history = st.session_state.experiment_settings['level_history'][current_factor]
            
            # 加入 log 輸出
            logger.info(f"開始生成各水準數據比較圖表，當前因子: {current_factor}")
            logger.info(f"level_history: {level_history}")
            logger.info(f"當前數據緩衝區: {st.session_state.mqtt_manager.get_data()}")
            
            # 創建比較圖表
            for sensor_type in ['pressure', 'vibration', 'rpm', 'current']:
                st.write(f"{sensor_type} 數據比較")
                fig = go.Figure()
                
                for level in ['1', '2', '3']:
                    if level_history[level]:
                        try:
                            values = []
                            for data in level_history[level]:
                                if sensor_type in data and isinstance(data[sensor_type], dict) and 'value' in data[sensor_type]:
                                    values.append(data[sensor_type]['value'])
                            if values:
                                fig.add_trace(go.Box(
                                    y=values,
                                    name=f"水準 {level}",
                                    boxpoints='all',
                                    jitter=0.3,
                                    pointpos=-1.8
                                ))
                                logger.info(f"水準 {level} 的 {sensor_type} 數據: {values}")
                            else:
                                logger.warning(f"水準 {level} 的 {sensor_type} 數據為空")
                        except Exception as e:
                            logger.error(f"處理水準 {level} 的 {sensor_type} 數據時發生錯誤: {str(e)}")
                    else:
                        logger.warning(f"水準 {level} 的歷史數據為空")
                
                fig.update_layout(
                    title=f"{sensor_type} 各水準數據分布",
                    yaxis_title="數值",
                    showlegend=True
                )
                st.plotly_chart(fig, use_container_width=True)
            
            logger.info("各水準數據比較圖表生成完成")
            
            # 添加停止實驗的按鈕
            if st.button("停止實驗"):
                st.session_state.experiment_settings['experiment_running'] = False
                st.success("實驗已停止")
                # 發布停止實驗的消息到 MQTT
                st.session_state.mqtt_manager.client.publish(
                    "jetsion/taguchi/device001/control_factors/stop",
                    "1"
                )
        else:
            st.warning("目前沒有進行中的實驗")
        
        # 自動更新機制
        time.sleep(1)
        st.rerun()

if __name__ == "__main__":
    ui = TaguchiUI()
    ui.run() 