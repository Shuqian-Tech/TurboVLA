#include "gemm.h"

#include <cmath>

namespace turbovla::hls {
namespace {

std::int8_t quantize_accumulator(std::int32_t value, float output_scale, bool relu) {
  float scaled = static_cast<float>(value) * output_scale;
  if (relu && scaled < 0.0f) {
    scaled = 0.0f;
  }
  const float rounded = std::round(scaled);
  if (rounded > 127.0f) {
    return 127;
  }
  if (rounded < -128.0f) {
    return -128;
  }
  return static_cast<std::int8_t>(rounded);
}

}  // namespace

GemmStatus gemm_int8(const std::int8_t* a,
                     const std::int8_t* b,
                     const std::int32_t* bias_acc,
                     std::int8_t* output,
                     int m,
                     int n,
                     int k,
                     float output_scale,
                     bool relu) {
#ifdef __SYNTHESIS__
#pragma HLS INTERFACE m_axi port = a offset = slave bundle = gmem0
#pragma HLS INTERFACE m_axi port = b offset = slave bundle = gmem1
#pragma HLS INTERFACE m_axi port = bias_acc offset = slave bundle = gmem2
#pragma HLS INTERFACE m_axi port = output offset = slave bundle = gmem3
#pragma HLS INTERFACE s_axilite port = m bundle = control
#pragma HLS INTERFACE s_axilite port = n bundle = control
#pragma HLS INTERFACE s_axilite port = k bundle = control
#pragma HLS INTERFACE s_axilite port = output_scale bundle = control
#pragma HLS INTERFACE s_axilite port = relu bundle = control
#pragma HLS INTERFACE s_axilite port = return bundle = control
#endif
  if (a == nullptr || b == nullptr || bias_acc == nullptr || output == nullptr || output_scale <= 0.0f ||
      m < 1 || m > kMaxM || n < 1 || n > kMaxN || k < 1 || k > kMaxK) {
    return output_scale <= 0.0f ? GemmStatus::kInvalidScale : GemmStatus::kInvalidShape;
  }

  for (int row = 0; row < m; ++row) {
    for (int col = 0; col < n; ++col) {
      std::int32_t accumulator = bias_acc[col];
      for (int inner = 0; inner < k; ++inner) {
#ifdef __SYNTHESIS__
#pragma HLS PIPELINE II = 1
#endif
        accumulator += static_cast<std::int32_t>(a[row * k + inner]) *
                       static_cast<std::int32_t>(b[inner * n + col]);
      }
      output[row * n + col] = quantize_accumulator(accumulator, output_scale, relu);
    }
  }
  return GemmStatus::kOk;
}

GemmStatus conv1x1_int8(const std::int8_t* input,
                        const std::int8_t* weights,
                        const std::int32_t* bias_acc,
                        std::int8_t* output,
                        int pixels,
                        int input_channels,
                        int output_channels,
                        float output_scale,
                        bool relu) {
  return gemm_int8(input, weights, bias_acc, output, pixels, output_channels, input_channels, output_scale, relu);
}

}  // namespace turbovla::hls

