/*
 * firmware_soc_v8b2_canonical.ino
 *
 * SOC Estimation -- V8B2 Canonical Package
 * Model: V7C Canonical MLP (Input(6)->Dense(64,ReLU)->Dense(32,ReLU)->Dense(1,linear))
 * Target: soc_method_b
 *
 * Modes (select with MODE_SELECT constant below):
 *   MODE_GOLDEN   -- 20 canonical golden vectors
 *   MODE_EXTENDED -- 120 samples (golden + IoT real)
 *   MODE_ANOMALY  -- 10 anomaly scenarios with detection rules
 *
 * Serial output schema (115200 baud):
 *   sample_id,mode,soc_final,inference_time_ms,free_heap,min_free_heap,max_alloc_heap,anomaly_flag,anomaly_code,status
 *
 * IMPORTANT:
 *   - Current must be in mA (not A). Scaler bounds assume mA.
 *   - SOC output is clipped to [0.0, 1.0] before reporting.
 *   - V7C has NOT yet been validated on this hardware. This run is the validation.
 *   - Do not modify scaler bounds. They must match canonical exactly.
 *
 * V8B2 Handoff Package -- PREPARED_PACKAGE_NOT_YET_EXECUTED_ON_ESP32
 * Date: 2026-05-16
 */

#include <Arduino.h>
#include "canonical_model_weights_v8b2.h"
#include "replay_vectors_v8b2.h"

// ============================================================
// MODE SELECTION -- Change this to switch replay mode
// ============================================================
#define MODE_GOLDEN   0
#define MODE_EXTENDED 1
#define MODE_ANOMALY  2

#define MODE_SELECT MODE_GOLDEN   // <-- CHANGE HERE: MODE_GOLDEN, MODE_EXTENDED, or MODE_ANOMALY

// ============================================================
// Anomaly detection thresholds (Phase 1: heuristic rules)
// These rules operate on raw input features without ESP32 reference data.
// ============================================================
#define VOLTAGE_MIN_THRESHOLD     3.80f   // V -- below training minimum
#define VOLTAGE_MAX_THRESHOLD     4.25f   // V -- above training maximum
#define CURRENT_MIN_THRESHOLD     10.0f   // mA -- current dropout detection
#define CURRENT_MAX_THRESHOLD     350.0f  // mA -- above training range
#define TEMP_MIN_THRESHOLD        0.0f    // C -- below safe operating range
#define TEMP_MAX_THRESHOLD        50.0f   // C -- above safe operating range
#define DELTA_VOLTAGE_MAX         0.10f   // V/sample -- abrupt voltage change
#define DELTA_CURRENT_MAX         200.0f  // mA/sample -- abrupt current change
#define DELTA_TEMP_MAX            10.0f   // C/sample -- abrupt temperature change
#define FLATLINE_WINDOW           5       // samples -- voltage flatline window
#define FLATLINE_TOLERANCE        0.005f  // V -- voltage variation considered flatline

// Anomaly codes (match expected_anomaly_code in anomaly_expected_flags_v8b2.csv)
#define ANOM_CODE_NONE            0
#define ANOM_CODE_VOLTAGE_RANGE   1
#define ANOM_CODE_CURRENT_RANGE   2
#define ANOM_CODE_TEMP_RANGE      3
#define ANOM_CODE_VOLTAGE_FLATLINE 4
#define ANOM_CODE_CURRENT_DROPOUT 5
#define ANOM_CODE_ABRUPT_DELTA_I  6

// ============================================================
// State variables for anomaly detection
// ============================================================
static float voltage_history[FLATLINE_WINDOW] = {0};
static int   history_count = 0;
static int   history_idx = 0;

// Heap tracking
static uint32_t min_free_heap_global = UINT32_MAX;

// ============================================================
// MLP Forward Pass
// Architecture: Input(6)->Dense(64,ReLU)->Dense(32,ReLU)->Dense(1,linear)->clip[0,1]
// ============================================================
float mlp_predict(const float x_raw[6]) {
  float x[MLP_INPUT_SIZE];
  float h0[MLP_L0_SIZE];
  float h1[MLP_L1_SIZE];
  float out;

  // Step 1: MinMax scale
  for (int i = 0; i < MLP_INPUT_SIZE; i++) {
    x[i] = (x_raw[i] - SCALER_MIN[i]) * SCALER_SCALE[i];
  }

  // Step 2: Layer 0 -- Dense(64, ReLU)
  for (int j = 0; j < MLP_L0_SIZE; j++) {
    float acc = B0[j];
    for (int i = 0; i < MLP_INPUT_SIZE; i++) {
      acc += W0[i][j] * x[i];
    }
    h0[j] = fmaxf(0.0f, acc);  // ReLU
  }

  // Step 3: Layer 1 -- Dense(32, ReLU)
  for (int j = 0; j < MLP_L1_SIZE; j++) {
    float acc = B1[j];
    for (int i = 0; i < MLP_L0_SIZE; i++) {
      acc += W1[i][j] * h0[i];
    }
    h1[j] = fmaxf(0.0f, acc);  // ReLU
  }

  // Step 4: Layer 2 -- Dense(1, linear)
  out = B2[0];
  for (int i = 0; i < MLP_L1_SIZE; i++) {
    out += W2[i][0] * h1[i];
  }

  // Step 5: Clip to [0.0, 1.0] -- required for V7C canonical model
  return fmaxf(0.0f, fminf(1.0f, out));
}

// ============================================================
// Anomaly Detection (Phase 1 -- heuristic thresholds only)
// Returns: anomaly_flag (0=clean, 1=anomaly), anomaly_code
// ============================================================
void detect_anomaly(const float feat[6], uint8_t *flag, uint8_t *code) {
  *flag = 0;
  *code = ANOM_CODE_NONE;

  float voltage  = feat[0];
  float temp     = feat[1];
  float current  = feat[2];
  float delta_v  = feat[3];
  float delta_i  = feat[5];

  // Rule 1: Voltage out of range
  if (voltage < VOLTAGE_MIN_THRESHOLD || voltage > VOLTAGE_MAX_THRESHOLD) {
    *flag = 1; *code = ANOM_CODE_VOLTAGE_RANGE; return;
  }

  // Rule 2: Current out of range (includes dropout detection)
  if (current < CURRENT_MIN_THRESHOLD) {
    *flag = 1; *code = ANOM_CODE_CURRENT_DROPOUT; return;
  }
  if (current > CURRENT_MAX_THRESHOLD) {
    *flag = 1; *code = ANOM_CODE_CURRENT_RANGE; return;
  }

  // Rule 3: Temperature out of range
  if (temp < TEMP_MIN_THRESHOLD || temp > TEMP_MAX_THRESHOLD) {
    *flag = 1; *code = ANOM_CODE_TEMP_RANGE; return;
  }

  // Rule 4: Abrupt delta voltage
  if (fabsf(delta_v) > DELTA_VOLTAGE_MAX) {
    *flag = 1; *code = ANOM_CODE_VOLTAGE_RANGE; return;
  }

  // Rule 5: Abrupt delta current
  if (fabsf(delta_i) > DELTA_CURRENT_MAX) {
    *flag = 1; *code = ANOM_CODE_ABRUPT_DELTA_I; return;
  }

  // Rule 6: Voltage flatline (5-sample window)
  voltage_history[history_idx % FLATLINE_WINDOW] = voltage;
  history_idx++;
  if (history_idx >= FLATLINE_WINDOW) {
    float v_min = voltage_history[0], v_max = voltage_history[0];
    for (int k = 1; k < FLATLINE_WINDOW; k++) {
      if (voltage_history[k] < v_min) v_min = voltage_history[k];
      if (voltage_history[k] > v_max) v_max = voltage_history[k];
    }
    if ((v_max - v_min) < FLATLINE_TOLERANCE) {
      *flag = 1; *code = ANOM_CODE_VOLTAGE_FLATLINE; return;
    }
  }
}

// ============================================================
// Print one serial output line
// ============================================================
void print_result(int sample_id, const char *mode_str, float soc_final,
                  float inference_ms, uint32_t free_heap, uint32_t min_free_heap,
                  uint32_t max_alloc_heap, uint8_t anomaly_flag, uint8_t anomaly_code,
                  const char *status) {
  Serial.print(sample_id);
  Serial.print(",");
  Serial.print(mode_str);
  Serial.print(",");
  Serial.print(soc_final, 6);
  Serial.print(",");
  Serial.print(inference_ms, 3);
  Serial.print(",");
  Serial.print(free_heap);
  Serial.print(",");
  Serial.print(min_free_heap);
  Serial.print(",");
  Serial.print(max_alloc_heap);
  Serial.print(",");
  Serial.print(anomaly_flag);
  Serial.print(",");
  Serial.print(anomaly_code);
  Serial.print(",");
  Serial.println(status);
}

// ============================================================
// Run one replay batch
// ============================================================
void run_replay(const float vectors[][6], const float references[], const uint8_t sat_flags[],
                int n_samples, const char *mode_str) {
  for (int s = 0; s < n_samples; s++) {
    // Copy input to local array (required for mlp_predict signature)
    float feat[6];
    for (int k = 0; k < 6; k++) feat[k] = vectors[s][k];

    // Anomaly detection (before inference)
    uint8_t a_flag = 0, a_code = 0;
    detect_anomaly(feat, &a_flag, &a_code);

    // MLP inference -- measure time
    uint32_t t_start = micros();
    float soc_final = mlp_predict(feat);
    uint32_t t_end = micros();
    float inference_ms = (float)(t_end - t_start) / 1000.0f;

    // Heap measurement
    uint32_t free_heap = esp_get_free_heap_size();
    uint32_t max_alloc = esp_get_maximum_allocated_block();
    if (free_heap < min_free_heap_global) min_free_heap_global = free_heap;

    // Status: PASS or WARN (WARN if sample is known saturated and clipped)
    const char *status = "PASS";
    if (sat_flags != NULL && sat_flags[s]) {
      status = "WARN_SAT";  // clipped -- expected behavior, not an error
    }
    if (a_flag) {
      status = "ANOMALY";
    }

    print_result(s, mode_str, soc_final, inference_ms,
                 free_heap, min_free_heap_global, max_alloc,
                 a_flag, a_code, status);

    delay(10);  // brief pause between samples for serial stability
  }
}

// ============================================================
// Setup
// ============================================================
void setup() {
  Serial.begin(115200);
  delay(2000);  // wait for serial to stabilize

  Serial.println("// V8B2 Canonical SOC Firmware -- NOT YET VALIDATED ON ESP32");
  Serial.println("// Model: V7C | Target: soc_method_b | Current unit: mA");
  Serial.println("// Schema: sample_id,mode,soc_final,inference_time_ms,free_heap,min_free_heap,max_alloc_heap,anomaly_flag,anomaly_code,status");

#if MODE_SELECT == MODE_GOLDEN
  Serial.println("// Mode: GOLDEN -- 20 canonical golden vectors");
  Serial.println("// Expected: MAE < 0.001 vs canonical reference");
  Serial.println("// BEGIN_GOLDEN");
  run_replay(GOLDEN_VECTORS, GOLDEN_REFERENCE, NULL, N_GOLDEN, "GOLDEN");
  Serial.println("// END_GOLDEN");

#elif MODE_SELECT == MODE_EXTENDED
  Serial.println("// Mode: EXTENDED -- 120 samples (golden + IoT real)");
  Serial.println("// Expected: MAE < 0.001 vs clipped reference; 6 WARN_SAT expected");
  Serial.println("// BEGIN_EXTENDED");
  run_replay(EXTENDED_VECTORS, EXTENDED_REFERENCE, EXTENDED_IS_SATURATED, N_EXTENDED, "EXTENDED");
  Serial.println("// END_EXTENDED");

#elif MODE_SELECT == MODE_ANOMALY
  Serial.println("// Mode: ANOMALY -- 10 scenarios with Phase 1 detection rules");
  Serial.println("// Expected: recall >= 0.90 on embedded-feasible scenarios");
  Serial.println("// BEGIN_ANOMALY");
  run_replay(ANOMALY_VECTORS, NULL, NULL, N_ANOMALY, "ANOMALY");
  Serial.println("// END_ANOMALY");

#else
  Serial.println("// ERROR: Invalid MODE_SELECT. Use MODE_GOLDEN, MODE_EXTENDED, or MODE_ANOMALY.");
#endif

  Serial.println("// DONE");
}

// ============================================================
// Loop -- nothing to do (replay runs once in setup)
// ============================================================
void loop() {
  delay(60000);
}
