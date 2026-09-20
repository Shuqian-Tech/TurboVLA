#include "fusion_action.h"

#include <algorithm>
#include <cmath>

namespace turbovla::hls {
namespace {

std::int8_t clamp_int8(float value) {
  return static_cast<std::int8_t>(std::max(-128.0f, std::min(127.0f, std::round(value))));
}

float hard_sigmoid(float value) {
  return std::max(0.0f, std::min(1.0f, 0.5f + value));
}

// The C++ reference uses tanh, but synthesizing the generic libm tanh pulls a
// large floating-point exp/divider network into the RTL.  This fixed-point
// table preserves the bounded [-1, 1] contract while keeping the PL path
// integer-only after the scale conversion.
std::int32_t tanh_q15(float value) {
  constexpr std::int32_t kInputScale = 16;
  constexpr std::int32_t kOutputScale = 32768;
  constexpr std::int32_t kLut[] = {-32768, -32641, -32431, -31114, -24982,
                                   0,      24982,  31114,  32431,  32641, 32767};
  int input = static_cast<int>(value * static_cast<float>(kInputScale));
  if (input <= -5 * kInputScale) {
    return -kOutputScale;
  }
  if (input >= 5 * kInputScale) {
    return kOutputScale - 1;
  }
  int interval = input / kInputScale;
  int remainder = input % kInputScale;
  if (remainder < 0) {
    --interval;
    remainder += kInputScale;
  }
  const int index = interval + 5;
  const int lower = kLut[index];
  const int upper = kLut[index + 1];
  return lower + ((upper - lower) * remainder) / kInputScale;
}

}  // namespace

GemmStatus gated_fusion_int8(const std::int8_t* visual,
                             const std::int8_t* language,
                             const std::int8_t* visual_weight,
                             const std::int8_t* language_weight,
                             const std::int8_t* gate_weight,
                             const std::int32_t* candidate_bias,
                             std::int8_t* output,
                             float candidate_scale,
                             float gate_scale,
                             float output_scale) {
  if (visual == nullptr || language == nullptr || visual_weight == nullptr || language_weight == nullptr ||
      gate_weight == nullptr || candidate_bias == nullptr || output == nullptr || candidate_scale <= 0.0f ||
      gate_scale <= 0.0f || output_scale <= 0.0f) {
    return GemmStatus::kInvalidScale;
  }
  std::int8_t visual_candidate[kVisualTokens * kHiddenDim];
  std::int8_t visual_gate[kVisualTokens * kHiddenDim];
  std::int8_t language_candidate[kHiddenDim];
  std::int8_t language_gate[kHiddenDim];
  std::int32_t zero_bias[kHiddenDim] = {};
  if (gemm_int8(visual, visual_weight, zero_bias, visual_candidate, kVisualTokens, kHiddenDim, kHiddenDim,
                1.0f, false) != GemmStatus::kOk ||
      gemm_int8(visual, gate_weight, zero_bias, visual_gate, kVisualTokens, kHiddenDim, kHiddenDim, 1.0f,
                false) != GemmStatus::kOk ||
      gemm_int8(language, language_weight, zero_bias, language_candidate, 1, kHiddenDim, kHiddenDim, 1.0f,
                false) != GemmStatus::kOk ||
      gemm_int8(language, gate_weight, zero_bias, language_gate, 1, kHiddenDim, kHiddenDim, 1.0f, false) !=
          GemmStatus::kOk) {
    return GemmStatus::kInvalidShape;
  }
  for (int token = 0; token < kVisualTokens; ++token) {
    for (int channel = 0; channel < kHiddenDim; ++channel) {
#ifdef __SYNTHESIS__
#pragma HLS PIPELINE II = 1
#endif
      const int index = token * kHiddenDim + channel;
      const float gate = hard_sigmoid(static_cast<float>(visual_gate[index] + language_gate[channel]) * gate_scale);
      const std::int32_t gate_q15 = static_cast<std::int32_t>(gate * 32768.0f);
      const float candidate = static_cast<float>(visual_candidate[index] + language_candidate[channel] +
                                                 candidate_bias[channel]) * candidate_scale;
      const std::int32_t candidate_q15 = tanh_q15(candidate);
      const std::int32_t candidate_int8 = (candidate_q15 * 127) >> 15;
      const std::int32_t mixed = ((32768 - gate_q15) * static_cast<std::int32_t>(visual[index]) +
                                  gate_q15 * candidate_int8) >> 15;
      output[index] = clamp_int8(static_cast<float>(mixed) / output_scale);
    }
  }
  return GemmStatus::kOk;
}

GemmStatus action_mlp_int8(const std::int8_t* fused_tokens,
                           const std::int8_t* state,
                           const std::int8_t* state_weight,
                           const std::int32_t* state_bias,
                           const std::int8_t* action_input_weight,
                           const std::int32_t* action_input_bias,
                           const std::int8_t* action_output_weight,
                           const std::int32_t* action_output_bias,
                           std::int8_t* output,
                           float output_scale) {
  if (fused_tokens == nullptr || state == nullptr || state_weight == nullptr || state_bias == nullptr ||
      action_input_weight == nullptr || action_input_bias == nullptr || action_output_weight == nullptr ||
      action_output_bias == nullptr || output == nullptr) {
    return GemmStatus::kInvalidShape;
  }
  std::int8_t pooled[kHiddenDim] = {};
  for (int token = 0; token < kVisualTokens; ++token) {
    for (int channel = 0; channel < kHiddenDim; ++channel) {
      pooled[channel] += static_cast<std::int8_t>(fused_tokens[token * kHiddenDim + channel] / kVisualTokens);
    }
  }
  std::int8_t state_projected[kHiddenDim];
  std::int8_t combined[kHiddenDim];
  if (gemm_int8(state, state_weight, state_bias, state_projected, 1, kHiddenDim, kStateDim, 1.0f, false) !=
      GemmStatus::kOk) {
    return GemmStatus::kInvalidShape;
  }
  for (int channel = 0; channel < kHiddenDim; ++channel) {
    combined[channel] = clamp_int8(static_cast<float>(pooled[channel]) + static_cast<float>(state_projected[channel]));
  }
  std::int8_t hidden[kActionHidden];
  if (gemm_int8(combined, action_input_weight, action_input_bias, hidden, 1, kActionHidden, kHiddenDim, 1.0f, true) !=
      GemmStatus::kOk) {
    return GemmStatus::kInvalidShape;
  }
  return gemm_int8(hidden, action_output_weight, action_output_bias, output, 1, kActionHorizon * kActionDim,
                   kActionHidden, output_scale, false);
}

}  // namespace turbovla::hls

// Flat HLS entry points are required by Vitis HLS 2025.1. The namespaced
// functions remain the source-level API used by the portable test benches.
int turbovla_gated_fusion_int8(
    const std::int8_t* visual,
    const std::int8_t* language,
    const std::int8_t* visual_weight,
    const std::int8_t* language_weight,
    const std::int8_t* gate_weight,
    const std::int32_t* candidate_bias,
    std::int8_t* output,
    float candidate_scale,
    float gate_scale,
    float output_scale) {
#ifdef __SYNTHESIS__
#pragma HLS INTERFACE m_axi port = visual offset = slave depth = 4096 bundle = gmem0
#pragma HLS INTERFACE m_axi port = language offset = slave depth = 128 bundle = gmem1
#pragma HLS INTERFACE m_axi port = visual_weight offset = slave depth = 16384 bundle = gmem2
#pragma HLS INTERFACE m_axi port = language_weight offset = slave depth = 16384 bundle = gmem3
#pragma HLS INTERFACE m_axi port = gate_weight offset = slave depth = 16384 bundle = gmem4
#pragma HLS INTERFACE m_axi port = candidate_bias offset = slave depth = 128 bundle = gmem5
#pragma HLS INTERFACE m_axi port = output offset = slave depth = 4096 bundle = gmem6
#pragma HLS INTERFACE s_axilite port = candidate_scale bundle = control
#pragma HLS INTERFACE s_axilite port = gate_scale bundle = control
#pragma HLS INTERFACE s_axilite port = output_scale bundle = control
#pragma HLS INTERFACE s_axilite port = return bundle = control
#endif
  return static_cast<int>(turbovla::hls::gated_fusion_int8(visual, language, visual_weight, language_weight,
                                                            gate_weight, candidate_bias, output, candidate_scale,
                                                            gate_scale, output_scale));
}

int turbovla_action_mlp_int8(
    const std::int8_t* fused_tokens,
    const std::int8_t* state,
    const std::int8_t* state_weight,
    const std::int32_t* state_bias,
    const std::int8_t* action_input_weight,
    const std::int32_t* action_input_bias,
    const std::int8_t* action_output_weight,
    const std::int32_t* action_output_bias,
    std::int8_t* output,
    float output_scale) {
#ifdef __SYNTHESIS__
#pragma HLS INTERFACE m_axi port = fused_tokens offset = slave depth = 4096 bundle = gmem0
#pragma HLS INTERFACE m_axi port = state offset = slave depth = 8 bundle = gmem1
#pragma HLS INTERFACE m_axi port = state_weight offset = slave depth = 1024 bundle = gmem2
#pragma HLS INTERFACE m_axi port = state_bias offset = slave depth = 128 bundle = gmem3
#pragma HLS INTERFACE m_axi port = action_input_weight offset = slave depth = 8192 bundle = gmem4
#pragma HLS INTERFACE m_axi port = action_input_bias offset = slave depth = 64 bundle = gmem5
#pragma HLS INTERFACE m_axi port = action_output_weight offset = slave depth = 5376 bundle = gmem6
#pragma HLS INTERFACE m_axi port = action_output_bias offset = slave depth = 84 bundle = gmem7
#pragma HLS INTERFACE m_axi port = output offset = slave depth = 84 bundle = gmem8
#pragma HLS INTERFACE s_axilite port = output_scale bundle = control
#pragma HLS INTERFACE s_axilite port = return bundle = control
#endif
  return static_cast<int>(turbovla::hls::action_mlp_int8(
      fused_tokens, state, state_weight, state_bias, action_input_weight, action_input_bias, action_output_weight,
      action_output_bias, output, output_scale));
}
