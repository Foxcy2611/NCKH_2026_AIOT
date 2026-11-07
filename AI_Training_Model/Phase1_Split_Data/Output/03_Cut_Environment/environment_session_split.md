# Phân chia session Environment V2

- Seed: `42`
- Tổng: `33` session
- Train: `27` session
- Validation: `3` session
- Test: `3` session
- Kế hoạch cắt: `10` clip × `5.0` giây/session
- `key_fan_5min.wav` và `silence_5min.wav` không thuộc bộ 33 session.
- Thư mục session đã chia: `D:\NCKH_2026\NCKH_2026_AIOT\AI_Training_Model\Dataset_TuThu_v_Kaggle\Out_Split_Session`

## Session Validation

| Nhóm | Session | File |
|---|---|---|
| podcast | podcast_session_04 | podcast_session_04.wav |
| fan | fan_session_04 | fan_session_04.wav |
| clap | clap_session_04 | clap_session_04.wav |

## Session Test

| Nhóm | Session | File |
|---|---|---|
| knock | knock_session_02 | knock_session_02.wav |
| room_noise | room_noise_session_06 | room_noise_session_06.wav |
| speech | speech_session_03 | speech_session_03.wav |

## Toàn bộ phân chia

| Split | Nhóm | Session | File | Số clip dự kiến |
|---|---|---|---|---:|
| train | clap | clap_session_01 | clap_session_01.wav | 10 |
| train | clap | clap_session_02 | clap_session_02.wav | 10 |
| train | clap | clap_session_03 | clap_session_03.wav | 10 |
| train | clap | clap_session_05 | clap_session_05.wav | 10 |
| train | clap | clap_session_06 | clap_session_06.wav | 10 |
| train | fan | fan_session_01 | fan_session_01.wav | 10 |
| train | fan | fan_session_02 | fan_session_02.wav | 10 |
| train | fan | fan_session_03 | fan_session_03.wav | 10 |
| train | fan | fan_session_06 | fan_session_06.wav | 10 |
| train | knock | knock_session_01 | knock_session_01.wav | 10 |
| train | knock | knock_session_03 | knock_session_03.wav | 10 |
| train | knock | knock_session_04 | knock_session_04.wav | 10 |
| train | knock | knock_session_05 | knock_session_05.wav | 10 |
| train | podcast | podcast_old_01 | podcast_5min.wav | 10 |
| train | podcast | podcast_session_02 | podcast_session_02.wav | 10 |
| train | podcast | podcast_session_03 | podcast_session_03.wav | 10 |
| train | podcast | podcast_session_05 | podcast_session_05.wav | 10 |
| train | podcast | podcast_session_06 | podcast_session_06.wav | 10 |
| train | room_noise | room_noise_session_01 | room_noise_session_01.wav | 10 |
| train | room_noise | room_noise_session_02 | room_noise_session_02.wav | 10 |
| train | room_noise | room_noise_session_03 | room_noise_session_03.wav | 10 |
| train | room_noise | room_noise_session_04 | room_noise_session_04.wav | 10 |
| train | room_noise | room_noise_session_05 | room_noise_session_05.wav | 10 |
| train | speech | speech_session_01 | speech_session_01.wav | 10 |
| train | speech | speech_session_02 | speech_session_02.wav | 10 |
| train | speech | speech_session_04 | speech_session_04.wav | 10 |
| train | speech | speech_session_05 | speech_session_05.wav | 10 |
| val | clap | clap_session_04 | clap_session_04.wav | 10 |
| val | fan | fan_session_04 | fan_session_04.wav | 10 |
| val | podcast | podcast_session_04 | podcast_session_04.wav | 10 |
| test | knock | knock_session_02 | knock_session_02.wav | 10 |
| test | room_noise | room_noise_session_06 | room_noise_session_06.wav | 10 |
| test | speech | speech_session_03 | speech_session_03.wav | 10 |
