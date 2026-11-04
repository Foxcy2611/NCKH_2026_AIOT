#ifndef NCKH_GATEWAY_TASKS_H
#define NCKH_GATEWAY_TASKS_H

#include <Arduino.h>

void TaskEspNow(void *parameter);
void TaskGatewayManager(void *parameter);
void TaskSensor(void *parameter);
void TaskConnManager(void *parameter);
void TaskMqttPublisher(void *parameter);
void TaskDisplayTFT(void *parameter);

#endif
