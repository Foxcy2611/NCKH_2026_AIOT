from pathlib import Path


# =============================================================================
# GENERAL
# =============================================================================

# ============================================================================
# CẤU HÌNH NGƯỜI DÙNG - chỉ cần sửa khối này trước khi chạy Quantize_Model.py
# ============================================================================

# Seed dùng để chọn representative samples và fine-tune QAT.
SEED = 44

# Tên ngắn dùng trong tên file đầu ra.
MODEL_VERSION = "V1"

# Thư mục checkpoint do Training_Model.py của Phase 2 tạo ra.
MODEL_SOURCE_FOLDER = "Output_Train_V1_SepConv2D_Flatten"

# Có thể đổi tên thư mục output nếu cần giữ nhiều lần lượng tử độc lập.
OUTPUT_FOLDER = f"Output_Quantize_{MODEL_VERSION}"


# ============================================================================
# CẤU HÌNH PIPELINE
# ============================================================================

THRESHOLD = 0.5

CLASS_NAMES = [
    "Asthma",
    "Non_Asthma",
]


# =============================================================================
# REPRESENTATIVE DATASET
# =============================================================================

REPRESENTATIVE_PER_CLASS = 50


# =============================================================================
# QAT
# =============================================================================

QAT_EPOCHS = 15
QAT_BATCH_SIZE = 32
QAT_LEARNING_RATE = 1e-5
QAT_PATIENCE = 5

QAT_REDUCE_LR_FACTOR = 0.5
QAT_REDUCE_LR_PATIENCE = 2
QAT_MIN_LR = 1e-6


# =============================================================================
# PATH
#
# Giả sử:
#
# AI_Training_Model/
# ├── Phase2_Preprocess_&_Traning/
# └── Phase3_Quantization_Model/
#     ├── config.py
#     └── ...
# =============================================================================

PHASE3_DIR = Path(__file__).resolve().parent

ROOT_DIR = PHASE3_DIR.parent


# =============================================================================
# PHASE 2
# =============================================================================

P2_DIR = (
    ROOT_DIR
    / "Phase2_Preprocess_&_Traning"
)

FEATURE_DIR = (
    P2_DIR
    / "Output_Preprocess"
)


# -----------------------------------------------------------------------------
# MODEL_SOURCE_FOLDER đã được chọn tại khối CẤU HÌNH NGƯỜI DÙNG ở đầu file.
# -----------------------------------------------------------------------------

MODEL_FILENAME = "Model_Asthma.keras"


TRAIN_OUTPUT_DIR = (
    P2_DIR
    / MODEL_SOURCE_FOLDER
)

MODEL_PATH = (
    TRAIN_OUTPUT_DIR
    / MODEL_FILENAME
)

NORMALIZATION_PATH = (
    TRAIN_OUTPUT_DIR
    / "Normalization_Params.txt"
)


# =============================================================================
# PHASE 3 OUTPUT
# =============================================================================

OUTPUT_DIR = PHASE3_DIR / OUTPUT_FOLDER

MODEL_DIR = OUTPUT_DIR / "models"
HEADER_DIR = OUTPUT_DIR / "headers"
QAT_DIR = OUTPUT_DIR / "qat"

PREDICTION_PATH = (
    OUTPUT_DIR
    / "Quantization_Predictions.csv"
)

REPORT_PATH = (
    OUTPUT_DIR
    / "Quantization_Report.txt"
)


# =============================================================================
# TFLITE OUTPUT
# =============================================================================

FP32_TFLITE_PATH = (
    MODEL_DIR
    / f"{MODEL_VERSION}_FP32.tflite"
)

PTQ_INT8_PATH = (
    MODEL_DIR
    / f"{MODEL_VERSION}_PTQ_INT8.tflite"
)

QAT_INT8_PATH = (
    MODEL_DIR
    / f"{MODEL_VERSION}_QAT_INT8.tflite"
)

PTQ_INT16X8_PATH = (
    MODEL_DIR
    / f"{MODEL_VERSION}_PTQ_INT16x8.tflite"
)


# =============================================================================
# HEADER OUTPUT
# =============================================================================

PTQ_INT8_HEADER = (
    HEADER_DIR
    / f"{MODEL_VERSION}_PTQ_INT8.h"
)

QAT_INT8_HEADER = (
    HEADER_DIR
    / f"{MODEL_VERSION}_QAT_INT8.h"
)

PTQ_INT16X8_HEADER = (
    HEADER_DIR
    / f"{MODEL_VERSION}_PTQ_INT16x8.h"
)


# =============================================================================
# QAT ARTIFACT
# =============================================================================

QAT_MODEL_PATH = (
    QAT_DIR
    / f"{MODEL_VERSION}_QAT.keras"
)

QAT_LOG_PATH = (
    QAT_DIR
    / "QAT_Training_Log.csv"
)
