#include <Arduino.h>

#include "Core_Logic/Patient_Node_App.h"

void setup(void) {
    PatientNodeApp_Init();
}

void loop(void) {
    PatientNodeApp_Run();
}
