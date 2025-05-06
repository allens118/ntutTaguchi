import paho.mqtt.client as mqtt
import time
import random
from datetime import datetime

class SensorSimulator:
    def __init__(self, device_id):
        self.device_id = device_id
        self.client = mqtt.Client()
        self.client.username_pw_set("jetsion", "jetsion")  # 添加認證
        self.client.connect("aiot.jetsion.com", 1883, 60)  # 使用正確的broker地址
        
        # 感測器參數
        self.pressure_range = (0, 120)  # 壓力範圍 (bar)
        self.vibration_range = (0, 10)  # 震動範圍 (mm/s)
        self.rpm_range = (0, 5000)     # 轉速範圍 (RPM)
        self.current_range = (0, 30)   # 電流範圍 (A)
        
        # 定義感測器訊號
        self.signals = [
            {"name": "pressure", "topic": f"jetsion/taguchi/{device_id}/pressure", "min": 0.0, "spec_low": 0.0, "spec_high": 100.0, "max": 120.0},
            {"name": "vibration", "topic": f"jetsion/taguchi/{device_id}/vibration", "min": 0.0, "spec_low": 0.0, "spec_high": 12.0, "max": 10.0},
            {"name": "rpm", "topic": f"jetsion/taguchi/{device_id}/rpm", "min": 0.0, "spec_low": 0.0, "spec_high": 3000.0, "max": 5000.0},
            {"name": "current", "topic": f"jetsion/taguchi/{device_id}/current", "min": 0.0, "spec_low": 0.0, "spec_high": 20.0, "max": 30.0}
        ]
        
    def generate_sensor_data(self):
        """產生模擬感測器數據"""
        data = {}
        for sig in self.signals:
            r = random.random()
            # 80% 在 Spec Low ~ Spec High
            if r < 0.8:
                if sig["name"] == "pressure":
                    value = random.uniform(0, 100)
                elif sig["name"] == "vibration":
                    value = random.uniform(0, 12)
                elif sig["name"] == "rpm":
                    value = random.uniform(0, 3000)
                elif sig["name"] == "current":
                    value = random.uniform(0, 20)
            # 10% 在 Min ~ Spec Low
            elif r < 0.9:
                if sig["name"] == "pressure":
                    value = random.uniform(0, 0)
                elif sig["name"] == "vibration":
                    value = random.uniform(0, 0)
                elif sig["name"] == "rpm":
                    value = random.uniform(0, 0)
                elif sig["name"] == "current":
                    value = random.uniform(0, 0)
            # 10% 在 Spec High ~ Max
            else:
                if sig["name"] == "pressure":
                    value = random.uniform(100, 120)
                elif sig["name"] == "vibration":
                    value = random.uniform(12, 10)
                elif sig["name"] == "rpm":
                    value = random.uniform(3000, 5000)
                elif sig["name"] == "current":
                    value = random.uniform(20, 30)
            
            # 依據範圍決定小數位數
            if sig["name"] in ["rpm"]:
                value = round(value, 0)
            else:
                value = round(value, 2)
            data[sig["name"]] = value
        return data
    
    def publish_data(self):
        """發布感測器數據到MQTT broker"""
        data = self.generate_sensor_data()
        
        # 發布到各個主題，直接發送數值字串
        for sig in self.signals:
            self.client.publish(sig["topic"], str(data[sig["name"]]))
            print(f"發送數據到 {sig['topic']}: {data[sig['name']]}")
        
        # 打印發送的數據
        print(f"發送數據: {data}")
    
    def run(self, interval=10):
        """運行感測器模擬"""
        try:
            while True:
                self.publish_data()
                time.sleep(interval)
        except KeyboardInterrupt:
            print("停止感測器模擬")
            self.client.disconnect()

class MultiSensorSimulator:
    def __init__(self):
        self.client = mqtt.Client()
        self.client.username_pw_set("jetsion", "jetsion")
        self.client.connect("aiot.jetsion.com", 1883, 60)
        # 定義每個訊號的 topic 與數值範圍
        self.signals = [
            {"name": "D20", "topic": "iii/device001/D20", "min": 0.0, "spec_low": 1.0, "spec_high": 999.0, "max": 1000.0},
            {"name": "peoplecounter", "topic": "iii/device001/peoplecounter", "min": 0.0, "spec_low": 0.0, "spec_high": 150.0, "max": 200.0},
            {"name": "current", "topic": "iii/device001/current", "min": 0.0, "spec_low": 0.0, "spec_high": 15.0, "max": 20.0},
            {"name": "rpm", "topic": "iii/device001/rpm", "min": 0.0, "spec_low": 0.0, "spec_high": 2000.0, "max": 5000.0},
            {"name": "WaterO2", "topic": "iii/device001/WaterO2", "min": 0.0, "spec_low": 4.0, "spec_high": 9.0, "max": 10.0},
            {"name": "WaterTemp", "topic": "iii/device001/WaterTemp", "min": 0.0, "spec_low": 5.0, "spec_high": 40.0, "max": 100.0},
            {"name": "WaterPH", "topic": "iii/device001/WaterPH", "min": 0.0, "spec_low": 4.0, "spec_high": 9.0, "max": 14.0},
        ]

    def generate_signal_data(self):
        """根據 Spec 區間產生合理的隨機數據"""
        data = {}
        for sig in self.signals:
            r = random.random()
            # 80% 在 Spec Low ~ Spec High
            if r < 0.8:
                value = random.uniform(sig["spec_low"], sig["spec_high"])
            # 10% 在 Min ~ Spec Low
            elif r < 0.9:
                value = random.uniform(sig["min"], sig["spec_low"])
            # 10% 在 Spec High ~ Max
            else:
                value = random.uniform(sig["spec_high"], sig["max"])
            # 依據範圍決定小數位數
            if sig["max"] > 100:
                value = round(value, 0)
            else:
                value = round(value, 2)
            data[sig["name"]] = value
        return data

    def publish_data(self):
        data = self.generate_signal_data()
        for sig in self.signals:
            self.client.publish(sig["topic"], str(data[sig["name"]]))
            print(f"發送數據到 {sig['topic']}: {data[sig['name']]}")
        print(f"發送多訊號數據: {data}")

    def run(self, interval=10):
        try:
            while True:
                self.publish_data()
                time.sleep(interval)
        except KeyboardInterrupt:
            print("停止多訊號模擬")
            self.client.disconnect()

if __name__ == "__main__":
    # 使用範例
    # simulator = SensorSimulator("device001")
    # simulator.run()
    # 若要測試多訊號模擬，請取消下行註解
    multi_sim = MultiSensorSimulator()
    multi_sim.run() 