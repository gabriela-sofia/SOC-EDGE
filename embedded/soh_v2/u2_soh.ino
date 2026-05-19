#include <Arduino.h>
#include <TensorFlowLite_ESP32.h>
#include <math.h>

#include "tensorflow/lite/micro/all_ops_resolver.h"
#include "tensorflow/lite/micro/micro_error_reporter.h"
#include "tensorflow/lite/micro/micro_interpreter.h"
#include "tensorflow/lite/schema/schema_generated.h"

#include "soh_model_data.h"

#define DEBUG_MODE 0

// ============================================================
// SOH v1.1
// Feature order:
//
// 0  cycle_number
// 1  voltage_V_mean
// 2  voltage_V_std
// 3  voltage_V_min
// 4  voltage_V_max
// 5  temperature_C_mean
// 6  temperature_C_std
// 7  temperature_C_min
// 8  temperature_C_max
// 9  current_est_mA_mean
// 10 current_est_mA_std
// 11 current_est_mA_min
// 12 current_est_mA_max
// 13 elapsed_time_s_min
// 14 elapsed_time_s_max
// 15 cycle_duration_s
// ============================================================

const int NUM_FEATURES = 16;

float data_min[] = {
  0.0000000000f,
  3.6647352538f,
  0.2214335144f,
  2.6996520000f,
  4.1314850000f,
  0.5208844484f,
  0.0006496795f,
  0.5200304000f,
  0.5221884000f,
  -741.5008595532f,
  0.8627372104f,
  -741.6675400000f,
  -705.0292000000f,
  0.0000000000f,
  2220.9153000000f,
  2220.9153000000f,
};

float data_max[] = {
  8200.0000000000f,
  3.7521895128f,
  0.2465770108f,
  2.7004573000f,
  4.1936490000f,
  41.8115859829f,
  0.7848671072f,
  41.0575070000f,
  42.9018630000f,
  -737.4410747281f,
  1.0958103939f,
  -737.6372000000f,
  -700.9983000000f,
  0.0000000000f,
  3606.3300000000f,
  3606.3300000000f,
};

// ============================================================

const tflite::Model* model = nullptr;
tflite::MicroInterpreter* interpreter = nullptr;

TfLiteTensor* input = nullptr;
TfLiteTensor* output = nullptr;

tflite::ErrorReporter* error_reporter = nullptr;

// ============================================================
// Tensor Arena
// ============================================================

constexpr int kTensorArenaSize = 48 * 1024;
uint8_t tensor_arena[kTensorArenaSize];

// ============================================================

void setup() {

  Serial.begin(115200);

  while (!Serial) {
    delay(10);
  }

  static tflite::MicroErrorReporter micro_error_reporter;
  error_reporter = &micro_error_reporter;

  model = tflite::GetModel(soh_model_tflite);

  if (model->version() != TFLITE_SCHEMA_VERSION) {
    Serial.println("ERROR_MODEL_SCHEMA_VERSION");
    return;
  }

  static tflite::AllOpsResolver resolver;

  static tflite::MicroInterpreter static_interpreter(
    model,
    resolver,
    tensor_arena,
    kTensorArenaSize,
    error_reporter
  );

  interpreter = &static_interpreter;

  if (interpreter->AllocateTensors() != kTfLiteOk) {
    Serial.println("ERROR_ALLOCATE_TENSORS");
    return;
  }

  input = interpreter->input(0);
  output = interpreter->output(0);

  Serial.println("READY");
}

// ============================================================

void loop() {

  if (Serial.available() <= 0) {
    return;
  }

  String line = Serial.readStringUntil('\n');
  line.trim();

  if (line.length() < 5) {
    return;
  }

  int firstComma = line.indexOf(',');

  if (firstComma == -1) {
    return;
  }

  String sample_id = line.substring(0, firstComma);
  sample_id.trim();

  String data = line.substring(firstComma + 1);

  char data_buffer[2048];
  data.toCharArray(data_buffer, sizeof(data_buffer));

  char* ptr = strtok(data_buffer, ",");

  int feature_count = 0;

  // ==========================================================
  // Parse + Scale
  // ==========================================================

  for (int i = 0; i < NUM_FEATURES; i++) {

    if (ptr == NULL) {
      break;
    }

    float raw_value = (float)atof(ptr);

    float range = data_max[i] - data_min[i];

    float scaled_value = 0.0f;

    if (fabs(range) > 0.000001f) {
      scaled_value = (raw_value - data_min[i]) / range;
    }

    // NÃO clipar features
    input->data.f[i] = scaled_value;

#if DEBUG_MODE

    Serial.print("DEBUG_FEATURE,");
    Serial.print(sample_id);
    Serial.print(",");
    Serial.print(i);
    Serial.print(",");
    Serial.print(raw_value, 10);
    Serial.print(",");
    Serial.println(scaled_value, 10);

#endif

    feature_count++;

    ptr = strtok(NULL, ",");

  }

  // ==========================================================
  // Validate feature count
  // ==========================================================

  if (feature_count != NUM_FEATURES) {

    Serial.print(sample_id);
    Serial.println(",-2.000000");

    Serial.flush();

    delay(5);

    return;
  }

  // ==========================================================
  // Inference
  // ==========================================================

  unsigned long t0 = micros();

  TfLiteStatus invoke_status = interpreter->Invoke();

  unsigned long t1 = micros();

  if (invoke_status != kTfLiteOk) {

    Serial.print(sample_id);
    Serial.println(",-1.000000");

    Serial.flush();

    delay(5);

    return;
  }

  float soh_raw = output->data.f[0];

#if DEBUG_MODE

  Serial.print("DEBUG_SOH_RAW,");
  Serial.print(sample_id);
  Serial.print(",");
  Serial.println(soh_raw, 10);

#endif

  // ==========================================================
  // Final clip
  // ==========================================================

  float soh_final = soh_raw;

  if (soh_final < 0.0f) {
    soh_final = 0.0f;
  }

  if (soh_final > 1.2f) {
    soh_final = 1.2f;
  }

  // ==========================================================
  // Metrics
  // ==========================================================

  unsigned long inference_time_us = t1 - t0;

  float inference_time_ms =
    inference_time_us / 1000.0f;

  uint32_t free_heap =
    ESP.getFreeHeap();

  uint32_t min_free_heap =
    ESP.getMinFreeHeap();

  uint32_t max_alloc_heap =
    ESP.getMaxAllocHeap();

  // ==========================================================
  // Output
  //
  // sample_id,
  // soh,
  // inference_time_ms,
  // free_heap,
  // min_free_heap,
  // max_alloc_heap
  // ==========================================================

  Serial.print(sample_id);
  Serial.print(",");

  Serial.print(soh_final, 6);
  Serial.print(",");

  Serial.print(inference_time_ms, 6);
  Serial.print(",");

  Serial.print(free_heap);
  Serial.print(",");

  Serial.print(min_free_heap);
  Serial.print(",");

  Serial.println(max_alloc_heap);

  Serial.flush();

  delay(5);
}