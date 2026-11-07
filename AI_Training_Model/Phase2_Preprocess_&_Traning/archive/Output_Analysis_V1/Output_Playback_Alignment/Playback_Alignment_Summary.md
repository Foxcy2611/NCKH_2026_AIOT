# Phân tích căn chỉnh Playback

Không huấn luyện lại model. Mọi crop dùng đúng pipeline V2.

## Ba source được chọn

| Hạng | Source | Số take sai | P(Non-Asthma) trung bình khi sai |
|---:|---|---:|---:|
| 1 | `AST_033` | 2 | 0.990849 |
| 2 | `AST_039` | 2 | 0.970403 |
| 3 | `AST_035` | 1 | 0.683286 |

## Kết quả theo source

### AST_033

| Variant | Crop | P(Non-Asthma) | Kết luận |
|---|---|---:|---|
| raw | 0.0-5.0 | 0.000003 | Asthma |
| raw | 0.5-5.5 | 0.000048 | Asthma |
| raw | 1.0-6.0 | 0.000014 | Asthma |
| take01 | 0.0-5.0 | 0.982902 | Non_Asthma |
| take01 | 0.5-5.5 | 0.000490 | Asthma |
| take01 | 1.0-6.0 | 0.001024 | Asthma |
| take02 | 0.0-5.0 | 0.998797 | Non_Asthma |
| take02 | 0.5-5.5 | 0.000414 | Asthma |
| take02 | 1.0-6.0 | 0.005312 | Asthma |

### AST_039

| Variant | Crop | P(Non-Asthma) | Kết luận |
|---|---|---:|---|
| raw | 0.0-5.0 | 0.000275 | Asthma |
| raw | 0.5-5.5 | 0.979863 | Non_Asthma |
| raw | 1.0-6.0 | 0.000356 | Asthma |
| take01 | 0.0-5.0 | 0.999116 | Non_Asthma |
| take01 | 0.5-5.5 | 0.550036 | Non_Asthma |
| take01 | 1.0-6.0 | 0.030666 | Asthma |
| take02 | 0.0-5.0 | 0.941689 | Non_Asthma |
| take02 | 0.5-5.5 | 0.632721 | Non_Asthma |
| take02 | 1.0-6.0 | 0.042096 | Asthma |

### AST_035

| Variant | Crop | P(Non-Asthma) | Kết luận |
|---|---|---:|---|
| raw | 0.0-5.0 | 0.000000 | Asthma |
| raw | 0.5-5.5 | 0.000001 | Asthma |
| raw | 1.0-6.0 | 0.000002 | Asthma |
| take01 | 0.0-5.0 | 0.683286 | Non_Asthma |
| take01 | 0.5-5.5 | 0.000896 | Asthma |
| take01 | 1.0-6.0 | 0.002119 | Asthma |
| take02 | 0.0-5.0 | 0.178797 | Asthma |
| take02 | 0.5-5.5 | 0.001711 | Asthma |
| take02 | 1.0-6.0 | 0.000044 | Asthma |
