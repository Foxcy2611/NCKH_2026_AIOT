import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
import joblib

print("⏳ Đang nạp dữ liệu...")
X = np.load("X_features.npy")
y = np.load("y_labels.npy")
LABELS = ["0_Asthma", "1_Others", "2_Background"]

print(f"Tổng số: {X.shape[0]} mẫu | {X.shape[1]} đặc trưng\n")

# Chia 80/20
X_train, X_test, y_train, y_test = train_test_split(
    X, y,
    test_size=0.2,
    random_state=42,
    stratify=y
)

scaler = StandardScaler()
X_train = scaler.fit_transform(X_train)
X_test  = scaler.transform(X_test)

np.save("X_train.npy", X_train)
np.save("X_test.npy",  X_test)
np.save("y_train.npy", y_train)
np.save("y_test.npy",  y_test)
joblib.dump(scaler, "scaler.pkl")

print("=== BÁO CÁO PHÂN MẢNH 80/20 ===")
print(f"Train: {X_train.shape[0]} mẫu  |  Test: {X_test.shape[0]} mẫu\n")

print("Phân bổ nhãn:")
for split_name, y_split in [("Train", y_train), ("Test", y_test)]:
    counts = np.bincount(y_split.astype(int))
    total  = len(y_split)
    row = ""
    for i, (lbl, cnt) in enumerate(zip(LABELS, counts)):
        pct = cnt / total * 100
        flag = " ⚠️ Lệch!" if pct < 10 or pct > 70 else ""
        row += f"  {lbl}: {cnt} ({pct:.1f}%){flag}"
    print(f"  {split_name}: {row}")