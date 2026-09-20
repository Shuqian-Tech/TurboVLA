#include "gemm.h"

#include <cstdint>
#include <iostream>

int main() {
  // Match the fixed HLS interface depths; runtime dimensions still exercise
  // the small 2x2x3 transaction while the unused tail remains zero.
  const std::int8_t a[16384] = {1, -2, 3, 4, 5, -6};
  const std::int8_t b[16384] = {2, 1, -1, 3, 4, -2};
  const std::int32_t bias[128] = {1, -3};
  std::int8_t output[16384] = {};
  if (turbovla_gemm_int8(a, b, bias, output, 2, 2, 3, 1.0f, false) != 0) {
    return 1;
  }
  const std::int8_t expected[4] = {17, -14, -20, 28};
  for (int index = 0; index < 4; ++index) {
    if (output[index] != expected[index]) {
      return 2;
    }
  }

  const std::int8_t conv_input[16384] = {1, 2, 3, 4};
  const std::int8_t conv_weights[16384] = {1, 2};
  const std::int32_t conv_bias[128] = {};
  std::int8_t conv_output[16384] = {};
  if (turbovla_conv1x1_int8(conv_input, conv_weights, conv_bias, conv_output, 2, 2, 1, 1.0f, false) != 0) {
    return 3;
  }
  if (conv_output[0] != 5 || conv_output[1] != 11) {
    return 4;
  }
  std::cout << "gemm HLS co-sim test passed\n";
  return 0;
}
