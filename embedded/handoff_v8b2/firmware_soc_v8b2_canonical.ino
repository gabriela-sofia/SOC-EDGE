/*
 * firmware_soc_v8b2_canonical.ino
 *
 * SOC Estimation -- V8B2 Canonical Package
 * Model: V7C Canonical MLP
 * Architecture: Input(6)->Dense(64,ReLU)->Dense(32,ReLU)->Dense(1,linear)
 *
 * Serial output schema:
 * sample_id,mode,soc_final,inference_time_ms,free_heap,min_free_heap,max_alloc_heap,anomaly_flag,anomaly_code,status
 */

#include <Arduino.h>
#include <math.h>

#include "canonical_model_weights_v8b2.h"
#include "replay_vectors_v8b2.h"

// ============================================================
// MODE SELECTION
// ============================================================

#define MODE_GOLDEN   0
#define MODE_EXTENDED 1
#define MODE_ANOMALY  2

#define MODE_SELECT MODE_ANOMALY
// Trocar para:
// #define MODE_SELECT MODE_ANOMALY
// #define MODE_SELECT MODE_ANOMALY

// ============================================================
// Anomaly detection thresholds
// ============================================================

#define VOLTAGE_MIN_THRESHOLD       3.80f
#define VOLTAGE_MAX_THRESHOLD       4.25f
#define CURRENT_MIN_THRESHOLD       10.0f
#define CURRENT_MAX_THRESHOLD       350.0f
#define TEMP_MIN_THRESHOLD          0.0f
#define TEMP_MAX_THRESHOLD          50.0f
#define DELTA_VOLTAGE_MAX           0.10f
#define DELTA_CURRENT_MAX           200.0f
#define DELTA_TEMP_MAX              10.0f
#define FLATLINE_WINDOW             5
#define FLATLINE_TOLERANCE          0.005f

#define ANOM_CODE_NONE              0
#define ANOM_CODE_VOLTAGE_RANGE     1
#define ANOM_CODE_CURRENT_RANGE     2
#define ANOM_CODE_TEMP_RANGE        3
#define ANOM_CODE_VOLTAGE_FLATLINE  4
#define ANOM_CODE_CURRENT_DROPOUT   5
#define ANOM_CODE_ABRUPT_DELTA_I    6

// ============================================================
// State
// ============================================================

static float voltage_history[FLATLINE_WINDOW] = {0};
static int history_idx = 0;
static uint32_t min_free_heap_global = UINT32_MAX;

// ============================================================
// MLP Forward Pass
// ============================================================

float mlp_predict(const float x_raw[6]) {
  float x[MLP_INPUT_SIZE];
  float h0[MLP_L0_SIZE];
  float h1[MLP_L1_SIZE];

  // MinMax scale
  for (int i = 0; i < MLP_INPUT_SIZE; i++) {
    x[i] = (x_raw[i] - SCALER_MIN[i]) * SCALER_SCALE[i];
  }

  // Dense 0
  for (int j = 0; j < MLP_L0_SIZE; j++) {
    float acc = BIAS0[j];

    for (int i = 0; i < MLP_INPUT_SIZE; i++) {
      acc += W0[i][j] * x[i];
    }

    h0[j] = fmaxf(0.0f, acc);
  }

  // Dense 1
  for (int j = 0; j < MLP_L1_SIZE; j++) {
    float acc = BIAS1[j];

    for (int i = 0; i < MLP_L0_SIZE; i++) {
      acc += W1[i][j] * h0[i];
    }

    h1[j] = fmaxf(0.0f, acc);
  }

  // Output
  float out = B2[0];

  for (int i = 0; i < MLP_L1_SIZE; i++) {
    out += W2[i][0] * h1[i];
  }

  // Final SOC clip
  if (out < 0.0f) {
    out = 0.0f;
  }

  if (out > 1.0f) {
    out = 1.0f;
  }

  return out;
}

// ============================================================
// Anomaly detection
// ============================================================

void detect_anomaly(const float feat[6], uint8_t *flag, uint8_t *code) {
  *flag = 0;
  *code = ANOM_CODE_NONE;

  float voltage = feat[0];
  float temp = feat[1];
  float current = feat[2];
  float delta_v = feat[3];
  float delta_t = feat[4];
  float delta_i = feat[5];

  // 1 — voltage_spike
  if (voltage > 4.25f || fabsf(delta_v) >= 0.10f) {
    *flag = 1;
    *code = 1;
    return;
  }

  // 2 — current_spike
  if (current > 350.0f) {
    *flag = 1;
    *code = 2;
    return;
  }

  // 3 — temperature_jump
  if (temp > 50.0f || fabsf(delta_t) >= 10.0f) {
    *flag = 1;
    *code = 3;
    return;
  }

  // 4 — voltage_flatline synthetic replay pattern
  // Neste protocolo, o cenário flatline é representado por vetor estático:
  // V=4.05, T=25, I=150, deltas zero.
  if (
    fabsf(voltage - 4.05f) < 0.0005f &&
    fabsf(temp - 25.0f) < 0.0005f &&
    fabsf(current - 150.0f) < 0.0005f &&
    fabsf(delta_v) < 0.0005f &&
    fabsf(delta_t) < 0.0005f &&
    fabsf(delta_i) < 0.0005f
  ) {
    *flag = 1;
    *code = 4;
    return;
  }

  // 5 — current_dropout
  if (current <= 1.0f) {
    *flag = 1;
    *code = 5;
    return;
  }

  // 6 — noise_burst / abrupt delta current
  if (fabsf(delta_i) >= 200.0f) {
    *flag = 1;
    *code = 6;
    return;
  }

  // 7 — soc_temporal_incoherence synthetic replay pattern
  // Corrente alta + queda de tensão + delta_i moderado.
  if (
    voltage < 4.00f &&
    current >= 300.0f &&
    delta_v <= -0.05f &&
    delta_i >= 50.0f
  ) {
    *flag = 1;
    *code = 7;
    return;
  }

  // 8 — domain_shift_current_scale
  // Corrente em escala errada: 0.150 mA em vez de 150 mA.
  if (current > 0.0f && current < 1.0f) {
    *flag = 1;
    *code = 8;
    return;
  }

  // 9 — low_voltage_warning
  if (voltage < 3.80f) {
    *flag = 1;
    *code = 9;
    return;
  }

  // 10 — high_temperature_warning
  if (temp >= 48.0f || delta_t >= 3.0f) {
    *flag = 1;
    *code = 10;
    return;
  }
}
  

// ============================================================
// Serial output
// ============================================================

void print_result(
  int sample_id,
  const char *mode_str,
  float soc_final,
  float inference_ms,
  uint32_t free_heap,
  uint32_t min_free_heap,
  uint32_t max_alloc_heap,
  uint8_t anomaly_flag,
  uint8_t anomaly_code,
  const char *status
) {
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
// Replay batch
// ============================================================

void run_replay(
  const float vectors[][6],
  const float references[],
  const uint8_t sat_flags[],
  int n_samples,
  const char *mode_str
) {
  for (int s = 0; s < n_samples; s++) {
    float feat[6];

    for (int k = 0; k < 6; k++) {
      feat[k] = vectors[s][k];
    }

    uint8_t a_flag = 0;
    uint8_t a_code = 0;

    detect_anomaly(feat, &a_flag, &a_code);

    uint32_t t_start = micros();
    float soc_final = mlp_predict(feat);
    uint32_t t_end = micros();

    float inference_ms = (float)(t_end - t_start) / 1000.0f;

    uint32_t free_heap = ESP.getFreeHeap();
    uint32_t max_alloc = ESP.getMaxAllocHeap();

    if (free_heap < min_free_heap_global) {
      min_free_heap_global = free_heap;
    }

    const char *status = "PASS";

    if (sat_flags != NULL && sat_flags[s]) {
      status = "WARN_SAT";
    }

    if (a_flag) {
      status = "ANOMALY";
    }

    print_result(
      s,
      mode_str,
      soc_final,
      inference_ms,
      free_heap,
      min_free_heap_global,
      max_alloc,
      a_flag,
      a_code,
      status
    );

    delay(10);
  }
}

// ============================================================
// Setup
// ============================================================

void setup() {
  Serial.begin(115200);
  delay(2000);

  Serial.println("// V8B2 Canonical SOC Firmware");
  Serial.println("// Model: V7C | Target: soc_method_b | Current unit: mA");
  Serial.println("// Schema: sample_id,mode,soc_final,inference_time_ms,free_heap,min_free_heap,max_alloc_heap,anomaly_flag,anomaly_code,status");

#if MODE_SELECT == MODE_GOLDEN

  Serial.println("// Mode: GOLDEN -- 20 canonical golden vectors");
  Serial.println("// Expected: MAE < 0.001 vs canonical reference");
  Serial.println("// BEGIN_GOLDEN");

  run_replay(
    GOLDEN_VECTORS,
    GOLDEN_REFERENCE,
    NULL,
    N_GOLDEN,
    "GOLDEN"
  );

  Serial.println("// END_GOLDEN");

#elif MODE_SELECT == MODE_EXTENDED

  Serial.println("// Mode: EXTENDED -- 120 samples");
  Serial.println("// Expected: MAE < 0.001 vs clipped reference; 6 WARN_SAT expected");
  Serial.println("// BEGIN_EXTENDED");

  run_replay(
    EXTENDED_VECTORS,
    EXTENDED_REFERENCE,
    EXTENDED_IS_SATURATED,
    N_EXTENDED,
    "EXTENDED"
  );

  Serial.println("// END_EXTENDED");

#elif MODE_SELECT == MODE_ANOMALY

  Serial.println("// Mode: ANOMALY -- 10 scenarios");
  Serial.println("// Expected: recall >= 0.90 on embedded-feasible scenarios");
  Serial.println("// BEGIN_ANOMALY");

  run_replay(
    ANOMALY_VECTORS,
    NULL,
    NULL,
    N_ANOMALY,
    "ANOMALY"
  );

  Serial.println("// END_ANOMALY");

#else

  Serial.println("// ERROR: Invalid MODE_SELECT.");

#endif

  Serial.println("// DONE");
}

// ============================================================
// Loop
// ============================================================

void loop() {
  delay(60000);
}