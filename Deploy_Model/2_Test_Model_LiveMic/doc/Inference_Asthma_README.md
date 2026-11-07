# Inference Asthma

`Inference_Asthma.cpp` chịu trách nhiệm duy nhất cho phần model:

1. Nạp model cuối `C4 V1 s44 / QAT_INT8` từ `Asthma_Model.h`.
2. Cấp tensor arena 1 MiB trong PSRAM.
3. Kiểm tra schema, kiểu INT8 và input `[1, 40, 129, 1]`.
4. Chuẩn hóa Mel-dB từ `[-80, 0]` về `[0, 1]` rồi lượng tử theo scale/zero-point
   của model.
5. Invoke, giải lượng tử output sigmoid và kết luận `0=Asthma`, `1=Non-Asthma`
   tại ngưỡng `0.5`.

Serial Monitor in cả dung lượng arena đã cấp và `arena_used_bytes()` để sau đó có
thể giảm arena một cách có căn cứ.

Header model hiện có: `include/Model_AI/Asthma_Model.h`.

API tensor trực tiếp cũ đã được xóa. Project này luôn đi qua preprocess C++ trước
khi inference.
