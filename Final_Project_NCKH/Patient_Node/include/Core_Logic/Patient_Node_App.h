#ifndef NCKH_PATIENT_NODE_APP_H
#define NCKH_PATIENT_NODE_APP_H

// Khởi tạo toàn bộ Patient Node. Gọi đúng một lần trong setup().
void PatientNodeApp_Init(void);

// Chạy một vòng điều phối ứng dụng. Gọi liên tục trong loop().
void PatientNodeApp_Run(void);

#endif /* NCKH_PATIENT_NODE_APP_H */
