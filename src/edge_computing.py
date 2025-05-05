import paho.mqtt.client as mqtt
import numpy as np
from datetime import datetime
import time
import random

class EdgeComputing:
    def __init__(self, device_id):
        self.device_id = device_id
        # 使用唯一的 client ID
        self.client = mqtt.Client(client_id=f"taguchi_edge_{int(time.time())}")
        self.client.username_pw_set("jetsion", "jetsion")
        
        # 連接狀態追蹤
        self.connected = False
        
        # 設定MQTT回調函數
        self.client.on_message = self.on_message
        self.client.on_connect = self.on_connect
        
        # 連接到 MQTT broker
        try:
            print("正在連接到 MQTT broker...")
            self.client.connect("jetsion.com", 1883, 60)
            print("MQTT 連接請求已發送")
        except Exception as e:
            print(f"MQTT 連接失敗: {str(e)}")
            return
            
        # 啟動 MQTT 客戶端
        self.client.loop_start()
        
        # 訂閱感測器主題
        self.client.subscribe(f"jetsion/taguchi/{device_id}/#")
        
        # 訂閱控制因子主題
        self.client.subscribe(f"jetsion/taguchi/{device_id}/control_factors/#")
        
        # 訂閱田口法相關主題
        self.client.subscribe(f"jetsion/device001/taguchi/control_factors/#")
        self.client.subscribe(f"jetsion/device001/taguchi/experiment_design/#")
        self.client.subscribe(f"jetsion/device001/taguchi/experiment_data/#")
        self.client.subscribe(f"jetsion/device001/taguchi/sn_ratio/#")
        self.client.subscribe(f"jetsion/device001/taguchi/experiment_results/#")
        self.client.subscribe(f"jetsion/device001/taguchi/experiment_status/#")
        self.client.subscribe(f"jetsion/device001/taguchi/control/#")
        
        # 控制因子定義
        self.control_factors = {
            "A": {
                "name": "壓力",
                "unit": "bar",
                "levels": {
                    "1": 25,
                    "2": 30,
                    "3": 35
                }
            },
            "B": {
                "name": "轉速",
                "unit": "RPM",
                "levels": {
                    "1": 1000,
                    "2": 2000,
                    "3": 3000
                }
            },
            "C": {
                "name": "電流",
                "unit": "A",
                "levels": {
                    "1": 5,
                    "2": 10,
                    "3": 15
                }
            }
        }
        
        # 實驗設計
        self.experiment_design = [
            {"A": 1, "B": 1, "C": 1},
            {"A": 1, "B": 2, "C": 2},
            {"A": 1, "B": 3, "C": 3},
            {"A": 2, "B": 1, "C": 2},
            {"A": 2, "B": 2, "C": 3},
            {"A": 2, "B": 3, "C": 1},
            {"A": 3, "B": 1, "C": 3},
            {"A": 3, "B": 2, "C": 1},
            {"A": 3, "B": 3, "C": 2}
        ]
        
        # 數據緩衝區
        self.data_buffer = {
            "pressure": [],
            "vibration": [],
            "rpm": [],
            "current": []
        }
        
        # 田口法相關數據
        self.taguchi_data = {
            "control_factors": {},
            "experiment_design": {},
            "experiment_data": {},
            "sn_ratio": {},
            "experiment_results": {},
            "experiment_status": {},
            "control": {}
        }
        
    def on_connect(self, client, userdata, flags, rc):
        """MQTT 連接回調"""
        if rc == 0:
            self.connected = True
            print("已成功連接到 MQTT broker")
            # 訂閱所有相關主題
            self.client.subscribe(f"jetsion/taguchi/{self.device_id}/#")
        else:
            self.connected = False
            print(f"連接失敗，返回碼: {rc}")
        
    def on_message(self, client, userdata, msg):
        """處理接收到的感測器數據和田口法相關數據"""
        try:
            print(f"收到訊息: {msg.topic} - {msg.payload.decode()}")
            
            # 如果是 S/N 比數據，直接跳過
            if "sn_ratio" in msg.topic:
                return
                
            # 處理感測器數據
            if msg.topic.startswith(f"jetsion/taguchi/{self.device_id}/"):
                value = float(msg.payload.decode())
                sensor_type = msg.topic.split("/")[-1]
                print(f"處理感測器數據: {sensor_type} = {value}")
                
                # 儲存數據
                self.data_buffer[sensor_type].append(value)
                print(f"{sensor_type} 緩衝區大小: {len(self.data_buffer[sensor_type])}")
                
                # 執行數據清洗和異常檢測
                self.data_cleaning(sensor_type)
                
                # 計算S/N比
                if len(self.data_buffer[sensor_type]) >= 10:
                    print(f"計算 {sensor_type} 的 S/N 比...")
                    sn_ratio = self.calculate_sn_ratio(self.data_buffer[sensor_type])
                    print(f"{sensor_type} 的 S/N 比: {sn_ratio}")
                    self.publish_sn_ratio(sensor_type, sn_ratio)
            
            # 處理控制因子設定
            elif msg.topic.startswith(f"jetsion/taguchi/{self.device_id}/control_factors/"):
                topic_parts = msg.topic.split("/")
                if len(topic_parts) >= 5:
                    factor = topic_parts[4]
                    if factor in self.control_factors:
                        if len(topic_parts) >= 6:
                            level = topic_parts[5]
                            if level in self.control_factors[factor]["levels"]:
                                value = float(msg.payload.decode())
                                self.control_factors[factor]["levels"][level] = value
                                print(f"更新控制因子 {factor} 水準 {level} 為 {value}")
            
            # 處理田口法相關數據
            elif msg.topic.startswith("jetsion/device001/taguchi/"):
                topic_parts = msg.topic.split("/")
                category = topic_parts[3]
                if len(topic_parts) > 4:
                    key = topic_parts[4]
                    if len(topic_parts) > 5:
                        sub_key = topic_parts[5]
                        if category in self.taguchi_data:
                            if key not in self.taguchi_data[category]:
                                self.taguchi_data[category][key] = {}
                            self.taguchi_data[category][key][sub_key] = msg.payload.decode()
                    else:
                        if category in self.taguchi_data:
                            self.taguchi_data[category][key] = msg.payload.decode()
                
        except Exception as e:
            print(f"處理數據時發生錯誤: {e}")
            
    def data_cleaning(self, sensor_type):
        """數據清洗和異常檢測"""
        if len(self.data_buffer[sensor_type]) < 3:
            return
            
        # 使用移動平均進行平滑，但不覆蓋原始數據
        window_size = 3
        smoothed_data = np.convolve(self.data_buffer[sensor_type], 
                                  np.ones(window_size)/window_size, 
                                  mode='valid')
        
        # 只保留最後一個平滑後的數據
        if len(smoothed_data) > 0:
            self.data_buffer[sensor_type][-1] = smoothed_data[-1]
        
    def calculate_sn_ratio(self, data):
        """計算S/N比
        使用望目特性S/N比公式：S/N = -10 * log10(σ²/μ²)
        其中：
        μ = 平均值
        σ = 標準差
        """
        if isinstance(data, dict):
            values = np.array(list(data.values()))
        else:
            values = np.array(data)
            
        # 確保有足夠的數據點
        if len(values) < 2:
            return 0
            
        mean = np.mean(values)
        std = np.std(values)
        
        # 避免除以零
        if mean == 0:
            return 0
            
        # 計算S/N比
        sn_ratio = -10 * np.log10((std**2) / (mean**2))
        
        # 判斷品質
        if sn_ratio > 10:
            quality = "良好"
        elif sn_ratio > 5:
            quality = "可接受"
        else:
            quality = "不佳"
            
        print(f"S/N 比: {round(sn_ratio, 2)} dB, 品質: {quality}")
        return round(sn_ratio, 2)
        
    def publish_sn_ratio(self, sensor_type, sn_ratio):
        """發布S/N比到MQTT broker"""
        topic = f"jetsion/taguchi/{self.device_id}/sn_ratio/{sensor_type}"
        print(f"發布 S/N 比到 {topic}: {sn_ratio}")
        self.client.publish(topic, str(sn_ratio))
        
    def publish_control_factors(self):
        """發布控制因子設定"""
        for factor, info in self.control_factors.items():
            # 發布因子設定
            self.client.publish(
                f"jetsion/taguchi/{self.device_id}/control_factors/setting/{factor}",
                f"{info['name']},{info['unit']}"
            )
            
            # 發布因子水準
            for level, value in info['levels'].items():
                self.client.publish(
                    f"jetsion/taguchi/{self.device_id}/control_factors/levels/{factor}/{level}",
                    str(value)
                )
            
            # 發布因子狀態
            self.client.publish(
                f"jetsion/taguchi/{self.device_id}/control_factors/status/{factor}",
                "active"
            )
        
    def publish_data(self, topic, value):
        """發布數據到指定主題"""
        full_topic = f"jetsion/taguchi/{self.device_id}/{topic}"
        try:
            self.client.publish(full_topic, str(value))
            print(f"已發布數據: {full_topic} = {value}")
            return True
        except Exception as e:
            print(f"發布數據失敗: {str(e)}")
            return False

    def generate_and_publish_data(self):
        """生成並發布感測器數據"""
        data = self.generate_sensor_data()
        success = True
        for sensor_type, value in data.items():
            if not self.publish_data(sensor_type, value):
                success = False
        return success

    def generate_sensor_data(self):
        """產生模擬感測器數據"""
        data = {}
        
        # 獲取當前控制因子的設定值
        current_factor = None
        current_level = None
        for factor, info in self.control_factors.items():
            for level, value in info['levels'].items():
                if value > 0:  # 如果該水準有設定值
                    current_factor = factor
                    current_level = level
                    break
            if current_factor:
                break
        
        # 根據控制因子生成數據
        if current_factor == "A":  # 溫度
            base_value = self.control_factors["A"]["levels"][current_level]
            data["pressure"] = round(base_value + random.uniform(-2, 2), 2)
            data["vibration"] = round(base_value * 0.5 + random.uniform(-1, 1), 2)
            data["rpm"] = round(base_value * 20 + random.uniform(-10, 10), 2)
            data["current"] = round(base_value * 0.8 + random.uniform(-3, 3), 2)
            
        elif current_factor == "B":  # 壓力
            base_value = self.control_factors["B"]["levels"][current_level]
            data["pressure"] = round(base_value + random.uniform(-5, 5), 2)
            data["vibration"] = round(base_value * 0.3 + random.uniform(-2, 2), 2)
            data["rpm"] = round(base_value * 15 + random.uniform(-30, 30), 2)
            data["current"] = round(base_value * 0.6 + random.uniform(-4, 4), 2)
            
        elif current_factor == "C":  # 轉速
            base_value = self.control_factors["C"]["levels"][current_level]
            data["pressure"] = round(base_value * 0.01 + random.uniform(-1, 1), 2)
            data["vibration"] = round(base_value * 0.02 + random.uniform(-2, 2), 2)
            data["rpm"] = round(base_value + random.uniform(-50, 50), 2)
            data["current"] = round(base_value * 0.4 + random.uniform(-20, 20), 2)
            
        else:  # 如果沒有設定控制因子，使用預設值
            data["pressure"] = round(random.uniform(0, 100), 2)
            data["vibration"] = round(random.uniform(0, 10), 2)
            data["rpm"] = round(random.uniform(0, 3000), 2)
            data["current"] = round(random.uniform(0, 20), 2)
        
        return data

    def simulate_experiment_data(self, design):
        """根據實驗設計產生模擬數據"""
        data = {}
        for sensor_type in self.data_buffer.keys():
            if sensor_type == "pressure":
                data[sensor_type] = round(random.uniform(0, 100), 2)
            elif sensor_type == "vibration":
                data[sensor_type] = round(random.uniform(0, 10), 2)
            elif sensor_type == "rpm":
                data[sensor_type] = round(random.uniform(0, 3000), 2)
            elif sensor_type == "current":
                data[sensor_type] = round(random.uniform(0, 20), 2)
        return data

    def run(self):
        """運行邊緣計算層"""
        try:
            print("開始運行邊緣計算層...")
            
            # 初始發布一次數據
            if self.connected:
                self.generate_and_publish_data()
                print("已發布初始數據")
            
            while True:
                if self.connected:
                    self.generate_and_publish_data()
                    print("已發布新數據")
                time.sleep(5)  # 每5秒更新一次
                
        except KeyboardInterrupt:
            print("停止邊緣計算層")
            self.client.loop_stop()
            self.client.disconnect()

if __name__ == "__main__":
    # 使用範例
    edge_computing = EdgeComputing("device001")
    edge_computing.run() 