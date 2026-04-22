import os
os.environ['TF_ENABLE_ONEDNN_OPTS'] = '0'
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'
# Ép TensorFlow im lặng (Chỉ in ra Lỗi thực sự, giấu đi các Warning)


import numpy as np
from keras.models import load_model
from sklearn.metrics import classification_report, confusion_matrix
import matplotlib.pyplot as plt
import seaborn as sns

# 1. Load lại dữ liệu test
X_test = np.load("X_test.npy")
y_test = np.load("y_test.npy")

# 2. Load lại model đã train (thấy bạn có file best_model.keras bên cột trái)
model = load_model("best_model.keras")

# 3. Định nghĩa lại LABELS (Dựa vào thư mục dataset của bạn)
LABELS = ["Asthma", "Others", "Background"] 

# ==========================================
# PHẦN CODE CŨ CỦA BẠN BẮT ĐẦU TỪ ĐÂY
# ==========================================

# Đánh giá trên tập test
loss, acc = model.evaluate(X_test, y_test, verbose=0)
print(f"Test Loss    : {loss:.4f}")
print(f"Test Accuracy: {acc:.4f} ({acc*100:.2f}%)")

y_pred = np.argmax(model.predict(X_test), axis=1)

print("\nClassification Report:")
print(classification_report(y_test, y_pred, target_names=LABELS))

# Confusion Matrix
cm = confusion_matrix(y_test, y_pred)
plt.figure(figsize=(6, 5))
sns.heatmap(cm, annot=True, fmt='d', cmap='Blues',
            xticklabels=LABELS, yticklabels=LABELS)
plt.title("Confusion Matrix")
plt.ylabel("Nhãn thực tế")
plt.xlabel("Nhãn dự đoán")
plt.tight_layout()
plt.savefig("confusion_matrix.png", dpi=150)
plt.show()