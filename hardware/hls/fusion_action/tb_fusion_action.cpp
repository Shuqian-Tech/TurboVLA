#include "fusion_action.h"

#include <algorithm>
#include <array>
#include <cstdint>
#include <iostream>

int main() {
  std::array<std::int8_t, turbovla::hls::kVisualTokens * turbovla::hls::kHiddenDim> visual{};
  std::array<std::int8_t, turbovla::hls::kHiddenDim> language{};
  std::array<std::int8_t, turbovla::hls::kHiddenDim * turbovla::hls::kHiddenDim> weights{};
  std::array<std::int32_t, turbovla::hls::kHiddenDim> bias{};
  std::array<std::int8_t, turbovla::hls::kVisualTokens * turbovla::hls::kHiddenDim> fused{};
  visual[0] = 2;
  visual[1] = -4;
  if (turbovla::hls::gated_fusion_int8(visual.data(), language.data(), weights.data(), weights.data(), weights.data(),
                                       bias.data(), fused.data(), 1.0f, 1.0f / 127.0f, 1.0f) !=
      turbovla::hls::GemmStatus::kOk) {
    return 1;
  }
  if (fused[0] != 1 || fused[1] != -2) {
    std::cerr << "fusion mismatch: " << static_cast<int>(fused[0]) << ", " << static_cast<int>(fused[1]) << '\n';
    return 2;
  }

  std::array<std::int8_t, turbovla::hls::kStateDim> state{};
  std::array<std::int8_t, turbovla::hls::kStateDim * turbovla::hls::kHiddenDim> state_weight{};
  std::array<std::int32_t, turbovla::hls::kHiddenDim> state_bias{};
  std::array<std::int8_t, turbovla::hls::kHiddenDim * turbovla::hls::kActionHidden> action_input_weight{};
  std::array<std::int32_t, turbovla::hls::kActionHidden> action_input_bias{};
  std::array<std::int8_t, turbovla::hls::kActionHidden * turbovla::hls::kActionHorizon * turbovla::hls::kActionDim>
      action_output_weight{};
  std::array<std::int32_t, turbovla::hls::kActionHorizon * turbovla::hls::kActionDim> action_output_bias{};
  std::array<std::int8_t, turbovla::hls::kActionHorizon * turbovla::hls::kActionDim> action{};
  if (turbovla::hls::action_mlp_int8(fused.data(), state.data(), state_weight.data(), state_bias.data(),
                                     action_input_weight.data(), action_input_bias.data(), action_output_weight.data(),
                                     action_output_bias.data(), action.data(), 1.0f) != turbovla::hls::GemmStatus::kOk) {
    return 3;
  }
  if (std::any_of(action.begin(), action.end(), [](std::int8_t value) { return value != 0; })) {
    return 4;
  }
  std::cout << "fusion/action C simulation passed\n";
  return 0;
}

