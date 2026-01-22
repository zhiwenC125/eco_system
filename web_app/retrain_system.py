import pandas as pd
import numpy as np
import joblib
import os
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import VotingClassifier, RandomForestClassifier
from sklearn.svm import SVC
from sklearn.linear_model import LogisticRegression

# 路径配置
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OLD_DATA_PATH = os.path.join(BASE_DIR, '../data/raw/data2.csv')
NEW_DATA_PATH = os.path.join(BASE_DIR, '../data/database/new_samples.csv')
MODEL_SAVE_PATH = os.path.join(BASE_DIR, '../models/')

FEATURE_NAMES = ['food', 'packaging', 'clothing', 'elec', 'water', 'paper', 'litter', 'commuting']

def evolve_model():
    print("--- 启动智慧进化系统 ---")
    
    # 1. 加载数据
    if not os.path.exists(OLD_DATA_PATH):
        print("错误：原始教材 data2.csv 不存在")
        return False
    
    df_old = pd.read_csv(OLD_DATA_PATH)
    
    if os.path.exists(NEW_DATA_PATH) and os.stat(NEW_DATA_PATH).st_size > 100:
        df_new = pd.read_csv(NEW_DATA_PATH)
        # 确保列名一致（如果有时间戳列则去掉）
        if 'timestamp' in df_new.columns:
            df_new = df_new.drop(columns=['timestamp'])
        
        # 数据融合
        print(f"融合新数据：{len(df_new)} 条记录")
        df_combined = pd.concat([df_old, df_new], ignore_index=True)
    else:
        print("没有足够的新数据进行融合，将使用原始数据优化...")
        df_combined = df_old

    # 2. 特征与标签分离
    X = df_combined[FEATURE_NAMES]
    y = df_combined['label']

    # 3. 重新标准化
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    # 4. 构建更强大的集成模型 (Voting)
    clf1 = RandomForestClassifier(n_estimators=100, random_state=42)
    clf2 = SVC(probability=True, random_state=42)
    clf3 = LogisticRegression(random_state=42)

    voting_clf = VotingClassifier(
        estimators=[('rf', clf1), ('svc', clf2), ('lr', clf3)],
        voting='soft'
    )

    # 5. 训练
    print("正在训练新一代 AI 模型...")
    voting_clf.fit(X_scaled, y)

    # 6. 保存新模型
    os.makedirs(MODEL_SAVE_PATH, exist_ok=True)
    joblib.dump(scaler, os.path.join(MODEL_SAVE_PATH, 'scaler.pkl'))
    joblib.dump(voting_clf, os.path.join(MODEL_SAVE_PATH, 'voting_classifier.pkl'))
    
    print("--- 进化完成：新模型已上线 ---")
    return True

if __name__ == "__main__":
    evolve_model()