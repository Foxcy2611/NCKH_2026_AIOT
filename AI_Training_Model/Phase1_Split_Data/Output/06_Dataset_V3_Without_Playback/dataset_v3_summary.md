# Dataset_Chia_V3 - Loai bo Playback

- Nguon: `Dataset_Chia_V2`
- Dich: `Dataset_Chia_V3`
- Tong WAV V2: 2287
- Playback loai bo: 160
- WAV giu lai trong V3: 2127
- Dung luong V3: 519394600 byte
- Copy moi trong lan chay nay: 2127
- File cu da verify: 0

| Class | Split | So WAV |
|---|---|---:|
| Asthma | train | 923 |
| Asthma | val | 30 |
| Asthma | test | 30 |
| Non_Asthma_Disease | train | 923 |
| Non_Asthma_Disease | val | 108 |
| Non_Asthma_Disease | test | 113 |

## Quy tac

- Khong copy bat ky WAV nao co trong playback manifest buoc 02.
- Manifest va suffix `__take01`/`__take02` phai trung khop tuyet doi.
- Moi WAV V3 duoc doi chieu SHA256 voi WAV V2.
- Dataset_Chia_V2 khong bi sua hoac di chuyen.
