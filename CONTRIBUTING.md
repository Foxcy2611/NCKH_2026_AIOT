# QUY ĐỊNH QUẢN LÝ SOURCE CODE BẰNG GIT & GITHUB

---

## 1. LUÔN KÉO CODE MỚI NHẤT VỀ TRƯỚC KHI CODE (BẮT BUỘC)
- Đầu mỗi buổi làm việc, luôn phải chuyển về nhánh `main` và bấm **Pull (Sync Changes)** để đồng bộ lấy bản code mới nhất về máy.  
- Việc này giúp hạn chế tối đa tình trạng xung đột (conflict) code với thành viên khác.

---

## 2. QUY TẮC LÀM VIỆC TRÊN NHÁNH (BRANCH)
- **KHÔNG BAO GIỜ** code và push trực tiếp lên nhánh `main` (Chỉ Leader mới có quyền này).  
- Mỗi task phải tạo một Branch riêng.  

---

## 3. CHỈ PUSH BẢN CODE CHẤT LƯỢNG NHẤT
- Có thể code nháp và commit nhiều lần lưu ở máy tính (local).  
- Nhưng khi quyết định **Push lên GitHub**, đó phải là phiên bản tốt nhất, có giá trị nhất của phiên làm việc đó.  
- Code đẩy lên **ĐẢM BẢO PHẢI CHẠY ĐƯỢC** (không bị lỗi biên dịch).

---

## 4. QUY TẮC VIẾT GHI CHÚ (COMMIT & PULL REQUEST)
- **Commit Message**: Ngắn gọn, đi thẳng vào vấn đề (VD: `"Thêm API lấy nhiệt độ DHT11"`).  
- Khi tạo **Pull Request (PR)** để Leader duyệt, **BẮT BUỘC** mô tả rõ trong phần Description:
  - Bạn đã làm/hoàn thành công việc gì?  
  - Code thêm mới, thay đổi thuật toán, hay fix bug ở đâu?  
  - Có file thư viện nào mới cần chú ý không?

---

## 5. CẨN THẬN VỚI FILE RÁC (QUAN TRỌNG)
- Nhìn kỹ các file màu xanh trên VS Code trước khi bấm dấu cộng (+).  
- **KHÔNG** đẩy các thư mục cấu hình cá nhân hoặc file tự sinh của phần mềm như:  
  - `.pio/`, `.vscode/`, `.idea/`  
  - file `.exe`, file build...  
- Nếu thấy chúng hiện lên, phải báo để thêm vào file `.gitignore` ngay lập tức.

---

## 6. XỬ LÝ XUNG ĐỘT (MERGE CONFLICT)
- Nếu tạo Pull Request mà GitHub báo lỗi Conflict (đụng code với người khác), tuyệt đối **không tự ý xóa code của người khác** để giữ code mình.  
- Phải nhắn lên group để cùng Trùm repo (Leader) xử lý.
