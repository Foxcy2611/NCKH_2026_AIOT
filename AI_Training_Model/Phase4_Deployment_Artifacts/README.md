# Phase 4 - Tạo dữ liệu kiểm thử deployment

Phase 4 chuẩn bị cùng một bộ WAV Test để kiểm tra model và pipeline C++ trên ESP32-S3. Phase này không huấn luyện hay lượng tử model.

Static profiling hiện hỗ trợ ba model được chốt tại mục D13.2:

- C4: `combo_pre0_mel40_fft2048__V1__s44 / QAT_INT8`.
- F0 baseline: `F0__V1__s43 / PTQ_INT8`.
- C3 đối chứng: `combo_mel40_fft2048__V1__s44 / QAT_INT8`.

## Phase này tạo gì?

```text
12 WAV Test cố định
  ├─ 6 Asthma
  └─ 6 Non-Asthma
        │
        ├─ preprocess riêng theo frontend của từng model
        │    ├─ Output_Static_Test_Tensors/<trial>/<method>/...
        │    └─ Deploy_Model/1.../include/<trial>/<method>/...
        │
        └─ chuyển WAV thành PCM16 mono 16 kHz, chưa preprocess
             ├─ LiveMic_PCM16_Test_Manifest.csv
             └─ Deploy_Model/2.../Raw_PCM16_Test_Samples.h
```

Hai nhánh dùng đúng cùng danh sách WAV:

- `Static_Test_Tensors.h` kiểm tra riêng model TFLite Micro, thời gian `Invoke()`, RAM và Tensor Arena.
- `Raw_PCM16_Test_Samples.h` kiểm tra toàn bộ `PCM16 → DSP C++ → Mel → model`.

## Ba script, ba nhiệm vụ riêng

### `Generate_Static_Test_Tensors.py`

Script bốc cố định 6 WAV mỗi lớp từ tập Test. Với mỗi target, script đọc `frontend_config`, normalization, input/output quantization và SHA-256 từ artifact `D_Quantization`/`D_Deployment`, rồi xuất tensor cùng CSV truy vết.

Mặc định script sinh đủ C4, F0 và C3. Có thể chỉ sinh một target:

```powershell
py -3.11 "AI_Training_Model/Phase4_Deployment_Artifacts/Generate_Static_Test_Tensors.py" --target C4_QAT_INT8
py -3.11 "AI_Training_Model/Phase4_Deployment_Artifacts/Generate_Static_Test_Tensors.py" --target F0_PTQ_INT8
py -3.11 "AI_Training_Model/Phase4_Deployment_Artifacts/Generate_Static_Test_Tensors.py" --target C3_QAT_INT8
```

Để tương thích luồng cũ, target F0 vẫn cập nhật hai file phẳng:

- `Output_Static_Test_Tensors/Static_Test_Tensors_Manifest.csv`.
- `Deploy_Model/1_Test_Model_Static_Profiling/include/Static_Test_Tensors.h`.

### `Generate_LiveMic_PCM16_Test_Header.py`

Script đọc manifest static để dùng lại đúng 12 WAV, chuyển chúng về PCM16 mono 16 kHz và lấy đúng 80.000 mẫu. Nhánh này chưa chạy DSP/Mel/model.

Playback `__take01/__take02` lấy đoạn `1,0-6,0 s`; các WAV khác lấy `0,0-5,0 s`.

### `Prepare_V3_PTQ_INT8_Static_Profiling.py`

Adapter tái lập riêng cho checkpoint `V3_HelloEdge / PTQ_INT8` của pipeline
Phase 2-3 hiện tại. Script tái sử dụng 12 input tensor C4 vì shape và input
quantization trùng tuyệt đối, nhưng bắt buộc suy luận lại output Python bằng V3
để phép đo parity không dùng output của model cũ.

Script sinh `Asthma_Model.h`, `Static_Test_Tensors.h`, manifest và metadata vào
`Output_Static_Test_Tensors/V3_HelloEdge/PTQ_INT8/`, đồng thời copy sang
`Deploy_Model/1_Test_Model_Static_Profiling/include/V3_HelloEdge/PTQ_INT8/`.

```powershell
py -3.11 "AI_Training_Model/Phase4_Deployment_Artifacts/Prepare_V3_PTQ_INT8_Static_Profiling.py"
```

Ba script không trùng nhau: script static tổng quát phục vụ shortlist Frontend,
script PCM16 phục vụ kiểm thử toàn pipeline DSP, còn adapter V3 đóng gói đúng
artifact Phase 3 vừa chọn để đo model tĩnh.

## Thứ tự chạy

Từ thư mục gốc repository:

```powershell
py -3.11 "AI_Training_Model/Phase4_Deployment_Artifacts/Generate_Static_Test_Tensors.py"
py -3.11 "AI_Training_Model/Phase4_Deployment_Artifacts/Generate_LiveMic_PCM16_Test_Header.py"
```

Sau đó dùng:

1. `Deploy_Model/1_Test_Model_Static_Profiling` để đo model tĩnh.
2. `Deploy_Model/2_Test_Model_LiveMic` để kiểm tra parity pipeline C++ và chạy mic thật.
3. `Deploy_Model/3_Model_Complete` để kiểm tra luồng gọn trước khi tích hợp Patient Node.

## Đầu ra cần kiểm tra

| Đầu ra | Yêu cầu |
|---|---|
| Static manifest/header C4 | 12 mẫu, input INT8 `[1,40,129,1]`, pre-emphasis `0.0`, FFT `2048` |
| Static manifest/header F0 | 12 mẫu, input INT8 `[1,64,129,1]`, pre-emphasis `0.97`, FFT `1024` |
| Static manifest/header C3 | 12 mẫu, input INT8 `[1,40,129,1]`, pre-emphasis `0.97`, FFT `2048` |
| PCM16 manifest/header | Cùng 12 source, mỗi mảng đúng 80.000 mẫu |
| Model/header pairing | `Asthma_Model.h` và `Static_Test_Tensors.h` phải nằm trong cùng thư mục `<trial>/<method>` |
