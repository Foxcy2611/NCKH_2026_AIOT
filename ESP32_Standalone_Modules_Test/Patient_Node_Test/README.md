# Patient_Node_Test — Final 2 M4 manual test

Firmware test thủ công cho Gateway M4 (ESP-NOW + AES-128-GCM).

## Chế độ hoạt động

Firmware **không tự gửi event** và **không tự retry**. Sau khi boot, nhập một lệnh trong Serial Monitor rồi nhấn Enter.

- `n`: tạo và gửi một event AES-GCM mới
- `d`: gửi lại **y nguyên packet cuối** để test duplicate
- `c`: sửa 1 byte ciphertext của packet cuối để test AES-GCM authentication failure
- `o`: gửi packet cũ hơn để test replay/out-of-order
- `r`: gửi lại y nguyên packet cuối để mô phỏng retry thủ công
- `x`: clear trạng thái pending của test harness, vẫn giữ last packet
- `h`: in help

Ba thuộc tính quan trọng của `d` và `r`: sequence, nonce, ciphertext và authentication tag của packet cũ được giữ nguyên.

## Serial

Baud: `115200`.

Sau boot sẽ thấy prompt `>`. Click vào terminal Patient_Node_Test, gõ ví dụ `n`, rồi Enter.
