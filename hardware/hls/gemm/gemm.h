#pragma once

#include <cstdint>

namespace turbovla::hls {

enum class GemmStatus : std::uint8_t {
  kOk = 0,
  kInvalidShape = 1,
  kInvalidScale = 2,
};

// Fixed upper bounds keep storage statically bounded for HLS. The runtime
// dimensions cover the Lite projection and action MLP matrices.
constexpr int kMaxM = 128;
constexpr int kMaxN = 128;
constexpr int kMaxK = 128;

GemmStatus gemm_int8(const std::int8_t* a,
                     const std::int8_t* b,
                     const std::int32_t* bias_acc,
                     std::int8_t* output,
                     int m,
                     int n,
                     int k,
                     float output_scale,
                     bool relu);

GemmStatus conv1x1_int8(const std::int8_t* input,
                        const std::int8_t* weights,
                        const std::int32_t* bias_acc,
                        std::int8_t* output,
                        int pixels,
                        int input_channels,
                        int output_channels,
                        float output_scale,
                        bool relu);

}  // namespace turbovla::hls

