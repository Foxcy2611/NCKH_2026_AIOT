#ifndef TEST_MODEL_STATIC_PROFILING_H
#define TEST_MODEL_STATIC_PROFILING_H

// Khoi tao model, tensor arena va kiem tra input/output INT8.
bool Setup_TinyML();

// Chay 12 tensor qua nhieu vong va in bao cao cho muc 10.2.
void Run_Static_Benchmark();

#endif  // TEST_MODEL_STATIC_PROFILING_H
