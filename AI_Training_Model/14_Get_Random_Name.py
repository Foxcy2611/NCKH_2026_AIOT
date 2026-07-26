"""
=========================================================
14. SET UP CHO FINAL TEST
- Tập dataset vô cùng lớn (1000 mẫu cho từng loại 0/1) nhưng
cái tên chúng na ná nhau (Dựa theo 3.py)
- Run để bốc bừa các dataset này để làm input raw cho mô hình
deploy C++ (Input cho 10.py)
- Nhằm thu được số lượng mẫu test lớn, đảm bảo model test qua đủ
bộ mẫu khác nhau mà cho ra kết quả đúng
=========================================================
"""

import os
import random
import glob

DIR_ASTHMA = "Dataset/0_Asthma"
DIR_NON_ASTHMA = "Dataset/1_Non_Asthma"

def print_random_names_only(directory):
    all_files = glob.glob(os.path.join(directory, "*.wav"))
    if not all_files:
        print(f"Không có file nào trong {directory}")
        return

    categories = {}
    
    for path in all_files:
        name = os.path.basename(path)
        parts = name.split('_')
        
        # Xử lý riêng tập Kaggle: Tìm thẳng từ khóa bệnh nằm trong tên file
        if name.startswith("Kaggle"):
            if "Bronchial" in name:
                prefix = "Kaggle_Bronchial"
            elif "COPD" in name:
                prefix = "Kaggle_COPD"
            elif "Healthy" in name:
                prefix = "Kaggle_Healthy"
            elif "Pneumonia" in name:
                prefix = "Kaggle_Pneumonia"
            else:
                prefix = "Kaggle_Other"
                
        # Nhóm các loại nhiễu và Augmentation
        elif name.startswith("Aug") or name.startswith("Noise"):
            if len(parts) >= 2:
                prefix = f"{parts[0]}_{parts[1]}"
            else:
                prefix = parts[0]
                
        # Nhóm file gốc
        elif name.startswith("Orig"):
            prefix = parts[0]
            
        else:
            prefix = parts[0]
            
        if prefix not in categories:
            categories[prefix] = []
        categories[prefix].append(name)

    # Bốc ngẫu nhiên 1 tên từ mỗi nhóm và in ra
    for prefix, files in categories.items():
        chosen_file = random.choice(files)
        print(chosen_file)

if __name__ == "__main__":
    print("=== TÊN FILE RANDOM TẬP ASTHMA ===")
    print_random_names_only(DIR_ASTHMA)
    
    print("\n=== TÊN FILE RANDOM TẬP NON-ASTHMA ===")
    print_random_names_only(DIR_NON_ASTHMA)