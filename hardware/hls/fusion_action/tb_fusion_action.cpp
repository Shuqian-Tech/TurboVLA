#include "fusion_action.h"

#include <cstdint>
#include <iostream>

int main() {
  std::int8_t visual[turbovla::hls::kVisualTokens * turbovla::hls::kHiddenDim] = {};
  std::int8_t language[turbovla::hls::kHiddenDim] = {};
  std::int8_t weights[turbovla::hls::kHiddenDim * turbovla::hls::kHiddenDim] = {};
  std::int32_t bias[turbovla::hls::kHiddenDim] = {};
  std::int8_t fused[turbovla::hls::kVisualTokens * turbovla::hls::kHiddenDim] = {};
  visual[0] = 2;
  visual[1] = -4;
  if (turbovla_gated_fusion_int8(visual, language, weights, weights, weights, bias, fused, 1.0f, 1.0f / 127.0f,
                                 1.0f) != 0) {
    return 1;
  }
  if (fused[0] != 1 || fused[1] != -2) {
    std::cerr << "fusion mismatch: " << static_cast<int>(fused[0]) << ", " << static_cast<int>(fused[1]) << '\n';
    return 2;
  }

  visual[0] = 0;
  visual[1] = 0;
  bias[0] = -3;
  bias[1] = 3;
  if (turbovla_gated_fusion_int8(visual, language, weights, weights, weights, bias, fused, 0.5f,
                                 1.0f / 127.0f, 1.0f) != 0) {
    return 3;
  }
  if (fused[0] != -55 || fused[1] != 54) {
    std::cerr << "negative interpolation mismatch: " << static_cast<int>(fused[0]) << ", "
              << static_cast<int>(fused[1]) << '\n';
    return 4;
  }

  std::int8_t state[turbovla::hls::kStateDim] = {};
  std::int8_t state_weight[turbovla::hls::kStateDim * turbovla::hls::kHiddenDim] = {};
  std::int32_t state_bias[turbovla::hls::kHiddenDim] = {};
  std::int8_t action_input_weight[turbovla::hls::kHiddenDim * turbovla::hls::kActionHidden] = {};
  std::int32_t action_input_bias[turbovla::hls::kActionHidden] = {};
  std::int8_t action_output_weight[turbovla::hls::kActionHidden * turbovla::hls::kActionHorizon *
                                   turbovla::hls::kActionDim] = {};
  std::int32_t action_output_bias[turbovla::hls::kActionHorizon * turbovla::hls::kActionDim] = {};
  std::int8_t action[turbovla::hls::kActionHorizon * turbovla::hls::kActionDim] = {};
  if (turbovla_action_mlp_int8(fused, state, state_weight, state_bias, action_input_weight, action_input_bias,
                               action_output_weight, action_output_bias, action, 1.0f) != 0) {
    return 5;
  }
  for (int index = 0; index < turbovla::hls::kActionHorizon * turbovla::hls::kActionDim; ++index) {
    if (action[index] != 0) {
      return 6;
    }
  }
  std::cout << "fusion/action C simulation passed\n";
  return 0;
}
