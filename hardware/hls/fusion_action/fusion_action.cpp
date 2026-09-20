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
      const float candidate = static_cast<float>(visual_candidate[index] + language_candidate[channel] + candidate_bias[channel]) *
                              candidate_scale;
      const float mixed = (1.0f - gate) * static_cast<float>(visual[index]) + gate * std::tanh(candidate) * 127.0f;
      output[index] = clamp_int8(mixed / output_scale);
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
