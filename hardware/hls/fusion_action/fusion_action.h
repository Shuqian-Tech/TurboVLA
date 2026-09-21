#pragma once

#include <cstdint>

#include "../gemm/gemm.h"

namespace turbovla::hls {

constexpr int kVisualTokens = 32;
constexpr int kHiddenDim = 128;
constexpr int kStateDim = 8;
constexpr int kActionHidden = 64;
constexpr int kActionHorizon = 12;
constexpr int kActionDim = 7;

GemmStatus gated_fusion_int8(const std::int8_t* visual,
                             const std::int8_t* language,
                             const std::int8_t* visual_weight,
                             const std::int8_t* language_weight,
                             const std::int8_t* gate_weight,
                             const std::int32_t* candidate_bias,
                             std::int8_t* output,
                             float candidate_scale,
                             float gate_scale,
                             float output_scale);

GemmStatus action_mlp_int8(const std::int8_t* fused_tokens,
                           const std::int8_t* state,
                           const std::int8_t* state_weight,
                           const std::int32_t* state_bias,
                           const std::int8_t* action_input_weight,
                           const std::int32_t* action_input_bias,
                           const std::int8_t* action_output_weight,
                           const std::int32_t* action_output_bias,
                           std::int8_t* output,
                           float output_scale);

}  // namespace turbovla::hls

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
    float output_scale);

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
    float output_scale);
