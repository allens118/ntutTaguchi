# Taguchi實驗系統模擬器

這是一個用於模擬Taguchi實驗系統的Python程式，包含感測器模擬和邊緣計算功能。

## 系統架構

### 感測器層
- 模擬壓力、震動、轉速和電流感測器
- 通過MQTT協議發送數據到broker

### 邊緣計算層
- 數據清洗和異常檢測
- S/N比計算
- 實驗參數管理

## 安裝說明

1. 建立虛擬環境：
```bash
python -m venv taguchi_env
```

2. 啟動虛擬環境：
- Windows:
```bash
.\taguchi_env\Scripts\activate
```
- Linux/Mac:
```bash
source taguchi_env/bin/activate
```

3. 安裝依賴套件：
```bash
pip install -r requirements.txt
```

## 使用說明

1. 啟動感測器模擬器：
```bash
python src/sensor_simulator.py
```

2. 啟動邊緣計算層：
```bash
python src/edge_computing.py
```

## MQTT主題說明

- 感測器數據：
  - `jetsion/Taguchi/<device_id>/pressure`
  - `jetsion/Taguchi/<device_id>/vibration`
  - `jetsion/Taguchi/<device_id>/rpm`
  - `jetsion/Taguchi/<device_id>/current`

- S/N比數據：
  - `jetsion/Taguchi/<device_id>/sn_ratio/<sensor_type>`

## 配置說明

- MQTT Broker: jetsion.com
- 預設端口: 1883
- 設備ID: device_001

## 注意事項

1. 確保MQTT broker已正確配置並運行
2. 根據實際需求調整感測器參數範圍
3. 可以通過修改程式碼來調整數據採樣頻率和計算參數 