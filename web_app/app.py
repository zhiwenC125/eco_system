from flask import Flask, render_template, request, jsonify
import joblib
import pandas as pd
import numpy as np
import os
import sys
import shap
import matplotlib
import datetime

# 必须在最顶层设置渲染后端，防止树莓派无显示器环境报错
matplotlib.use('Agg')
import matplotlib.pyplot as plt

# 确保导入 hardware 接口
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from hardware.stm32_interface import STM32Interface

app = Flask(__name__)

# --- 1. 路径管理 ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = os.path.join(BASE_DIR, '../models/')
DB_PATH = os.path.join(BASE_DIR, '../data/database/new_samples.csv')
STATIC_DIR = os.path.join(BASE_DIR, 'static')

os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
os.makedirs(STATIC_DIR, exist_ok=True)

# --- 2. 加载模型组件 ---
try:
    scaler = joblib.load(os.path.join(MODEL_PATH, 'scaler.pkl'))
    voting_model = joblib.load(os.path.join(MODEL_PATH, 'voting_classifier.pkl'))
    print("AI 监测系统：模型与标准化器已准备就绪")
except Exception as e:
    print(f"加载模型失败: {e}")
    raise

# --- 3. 初始化硬件接口 (树莓派 5 默认串口) ---
stm32 = STM32Interface(port='/dev/ttyAMA0', baudrate=115200)

# 特征名定义 (必须与训练时一致)
FEATURE_NAMES = ['food', 'packaging', 'clothing&shoes', 'electricity', 'hot water', 'paper', 'litter', 'commuting']

# --- 4. 核心逻辑函数 ---

def _load_bg():
    """动态加载背景数据，为 SHAP 提供基准"""
    try:
        if os.path.exists(DB_PATH) and os.stat(DB_PATH).st_size > 500:
            hist = pd.read_csv(DB_PATH).tail(30)
            # 这里的字段对齐逻辑需要根据你的 CSV 表头调整
            bg_df = hist[FEATURE_NAMES] # 假设新版存储已经对齐了特征名
            return scaler.transform(bg_df)
    except:
        pass
    return np.zeros((1, 8))

def _predict_proba_fn(x):
    """适配 SHAP 的预测封装"""
    return voting_model.predict_proba(pd.DataFrame(x, columns=FEATURE_NAMES))

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/predict', methods=['POST'])
def predict():
    try:
        user_input = request.get_json()
        if not user_input:
            return jsonify({"status": "error", "message": "未收到请求数据"})
        
        sid = user_input.get('student_id', 'Unknown')
        
        # 串口数据获取
        try:
            live_hw = stm32.get_realtime_data(sid)
            if not live_hw: live_hw = {"electricity": 450.0, "hot_water": 12.0}
        except:
            live_hw = {"electricity": 450.0, "hot_water": 12.0}

        # --- 核心修正 1：定义 raw_values 列表 ---
        # 必须先创建这个列表，后续的 DataFrame 和存储逻辑才能使用它
        raw_values = [
            float(user_input.get('food', 500)),
            float(user_input.get('packaging', 50)),
            float(user_input.get('clothing', 100)), # 这里的键名对应前端 ID
            float(live_hw['electricity']),
            float(live_hw['hot_water']),
            float(user_input.get('paper', 20)),
            float(user_input.get('litter', 30)),
            float(user_input.get('commuting', 5))
        ]

        # --- 核心修正 2：确保列名严格对齐 (消除 Warning) ---
        input_df = pd.DataFrame([raw_values], columns=FEATURE_NAMES)
        
        # 标准化
        input_scaled = scaler.transform(input_df)
        
        # 将标准化后的结果重新包装成带列名的 DF (这是消除 UserWarning 的关键)
        input_scaled_named = pd.DataFrame(input_scaled, columns=FEATURE_NAMES)
        
        # 进行预测
        prediction = int(voting_model.predict(input_scaled_named)[0])

        # --- SHAP 逻辑 ---
        try:
            bg = _load_bg()
            explainer = shap.KernelExplainer(_predict_proba_fn, bg)
            shap_raw = explainer.shap_values(input_scaled_named, nsamples=100)
            
            # 1. 核心修复：处理 expected_value 和 shap_values 的维度
            # 针对多分类逻辑：获取当前预测类别 (prediction) 对应的数值
            if isinstance(shap_raw, list):
                # 如果是列表，说明是多分类
                idx = min(prediction, len(shap_raw) - 1)
                sv_numeric = np.array(shap_raw[idx]).flatten()
                ev_raw = explainer.expected_value[idx]
            else:
                # 如果是单数组
                sv_numeric = np.array(shap_raw).flatten()
                ev_raw = explainer.expected_value

            # 关键：使用 np.asscalar 或 np.ravel 确保 base_v 是一个纯粹的数字
            # 我们通过这种方式彻底干掉 "can only convert an array of size 1" 报错
            base_v = float(np.ravel(ev_raw)[0])

            # 2. 构造 Explanation 对象
            exp = shap.Explanation(
                values=sv_numeric[:8].astype(np.float64),
                base_values=base_v,
                data=np.array(raw_values).astype(np.float64), # 直接使用原始输入数值
                feature_names=FEATURE_NAMES
            )

            # 3. 绘图与保存 (增加异常保护)
            plt.close('all') # 彻底清理内存
            plt.figure(figsize=(10, 6))
            
            # 使用条形图展示贡献
            shap.plots.bar(exp, show=False)
            plt.title(f"Impact Analysis | Student ID: {sid}", fontsize=12)
            
            # 保存路径
            plot_path = os.path.join(STATIC_DIR, 'shap_output.png')
            
            # 确保目录存在并保存
            plt.savefig(plot_path, bbox_inches='tight', dpi=120)
            plt.close()
            print(f"✅ SHAP 图表更新成功: {plot_path}")

        except Exception as e:
            # 即使 SHAP 失败，也不要让整个 predict 崩溃
            print(f"❌ SHAP 深度报错: {e}")
            import traceback
            traceback.print_exc() # 打印到终端看具体的行号

        # --- 核心修正 3：使用已定义的 raw_values 存储 ---
        save_with_identity(sid, raw_values, prediction)

        return jsonify({
            "status": "success",
            "prediction": {0:"低碳型学生", 1:"一般型学生", 2:"高碳型学生"}.get(prediction),
            "live_hw": live_hw,
            "shap_img": "/static/shap_output.png"
        })

    except Exception as e:
        import traceback
        traceback.print_exc() # 打印完整错误堆栈到终端
        return jsonify({"status": "error", "message": str(e)})

def save_with_identity(student_id, values, label):
    """
    保存包含时间戳和学号的完整对齐记录
    """
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    file_exists = os.path.isfile(DB_PATH)
    try:
        with open(DB_PATH, 'a', encoding='utf-8') as f:
            if not file_exists or os.stat(DB_PATH).st_size == 0:
                # 重新定义 CSV 结构，增加时间戳和学号
                f.write("timestamp,student_id,food,packaging,clothing,electricity,hot_water,paper,litter,commuting,label\n")
            
            line = f"{timestamp},{student_id}," + ",".join(map(str, values)) + f",{label}\n"
            f.write(line)
        print(f"日志：学号 {student_id} 的数据已于 {timestamp} 入库")
    except Exception as e:
        print(f"存储失败: {e}")

# --- 管理与进化路由 ---
@app.route('/admin')
def admin_panel():
    new_count = 0
    if os.path.exists(DB_PATH):
        with open(DB_PATH, 'r') as f:
            new_count = max(0, len(f.readlines()) - 1)
    return render_template('admin.html', new_count=new_count)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)