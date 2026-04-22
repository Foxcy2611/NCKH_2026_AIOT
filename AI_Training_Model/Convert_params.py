# Chạy file này 1 lần trong thư mục Python project
import joblib
import numpy as np

scaler = joblib.load("scaler.pkl")

mean = scaler.mean_      # shape (240,)
std  = scaler.scale_     # shape (240,)

with open("scaler_params.h", "w") as f:
    f.write("#pragma once\n\n")
    f.write(f"#define FEATURE_DIM  {len(mean)}\n\n")
    
    # Viết mảng MEAN
    f.write("const float SCALER_MEAN[FEATURE_DIM] = {\n")
    for i, v in enumerate(mean):
        comma = "," if i < len(mean) - 1 else ""
        newline = "\n" if (i + 1) % 8 == 0 else ""
        f.write(f"  {v:.8f}f{comma}{newline}")
    f.write("\n};\n\n")
    
    # Viết mảng STD
    f.write("const float SCALER_STD[FEATURE_DIM] = {\n")
    for i, v in enumerate(std):
        comma = "," if i < len(std) - 1 else ""
        newline = "\n" if (i + 1) % 8 == 0 else ""
        f.write(f"  {v:.8f}f{comma}{newline}")
    f.write("\n};\n")

print(f"✅ Đã tạo scaler_params.h — {len(mean)} phần tử")