import pandas as pd
import numpy as np
import joblib
import os
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier, VotingClassifier
from sklearn.svm import SVC

class CarbonModelTrainer:
    def __init__(self, data_path='data/raw/data2.csv', model_dir='models'):
        self.data_path = data_path
        self.model_dir = model_dir
        self.scaler = StandardScaler()
        self.kmeans = KMeans(n_clusters=3, random_state=42, n_init=10)
        
        # 1. 定义基分类器
        rf = RandomForestClassifier(n_estimators=100, random_state=42)
        gb = GradientBoostingClassifier(n_estimators=100, random_state=42)
        svc = SVC(probability=True, random_state=42) # 设置 probability 为 True 方便后续做 Soft Voting

        # 2. 初始化 Voting 分类器
        # 'soft' 投票基于概率（通常更准），'hard' 投票基于分类计数
        self.voting_clf = VotingClassifier(
            estimators=[('rf', rf), ('gb', gb), ('svc', svc)],
            voting='soft' 
        )
        
        if not os.path.exists(self.model_dir):
            os.makedirs(self.model_dir)

    def load_data(self):
        if not os.path.exists(self.data_path):
            raise FileNotFoundError(f"无法找到数据文件: {self.data_path}")
        return pd.read_csv(self.data_path)

    def _get_label_mapping(self, df, clusters):
        """确保 0=低碳, 1=中碳, 2=高碳"""
        cluster_emissions = [df[clusters == i].sum(axis=1).mean() for i in range(3)]
        rank_idx = np.argsort(cluster_emissions)
        return {rank_idx[0]: 0, rank_idx[1]: 1, rank_idx[2]: 2}

    def train_pipeline(self):
        print("开始执行训练流水线 (使用 Voting Classifier)...")
        
        df = self.load_data()
        feature_names = df.columns.tolist()

        # 预处理
        scaled_data = self.scaler.fit_transform(df)

        # 聚类生成伪标签
        clusters = self.kmeans.fit_predict(scaled_data)
        mapping = self._get_label_mapping(df, clusters)
        final_labels = np.array([mapping[c] for c in clusters])
        
        df['label'] = final_labels

        # 训练集成模型
        print("正在训练 Voting 集成模型 (RF + GBDT + SVC)...")
        self.voting_clf.fit(df[feature_names], final_labels)

        # 保存所有组件
        self.save_artifacts()
        
        print(f"训练完成！类别分布：\n{df['label'].value_counts().sort_index()}")
        return df

    def save_artifacts(self):
        joblib.dump(self.scaler, os.path.join(self.model_dir, 'scaler.pkl'))
        joblib.dump(self.kmeans, os.path.join(self.model_dir, 'kmeans_cluster.pkl'))
        # 注意：这里保存的是 voting_clf
        joblib.dump(self.voting_clf, os.path.join(self.model_dir, 'voting_classifier.pkl'))
        print(f"所有模型组件已保存至 {self.model_dir}")

if __name__ == "__main__":
    trainer = CarbonModelTrainer()
    trainer.train_pipeline()