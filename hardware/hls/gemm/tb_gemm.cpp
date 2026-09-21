#include "gemm.h"

#include <cstdint>
#include <iostream>

namespace {

bool check_equal(const std::int8_t* actual, const std::int8_t* expected, int count, const char* name) {
  for (int index = 0; index < count; ++index) {
    if (actual[index] != expected[index]) {
      std::cerr << name << " mismatch at " << index << ": " << static_cast<int>(actual[index]) << " != "
                << static_cast<int>(expected[index]) << '\n';
      return false;
    }
  }
  return true;
}

}  // namespace

int main() {
  const std::int8_t a[6] = {1, -2, 3, 4, 5, -6};
  const std::int8_t b[6] = {2, 1, -1, 3, 4, -2};
  const std::int32_t bias[2] = {1, -3};
  std::int8_t output[4] = {};
  const std::int8_t expected[4] = {17, -14, -20, 28};
  if (turbovla_gemm_int8(a, b, bias, output, 2, 2, 3, 1.0f, false) != 0) {
    return 1;
  }
  if (!check_equal(output, expected, 4, "gemm")) {
    return 2;
  }

  std::int8_t conv_output[2] = {};
  const std::int8_t conv_expected[2] = {5, 11};
  const std::int8_t conv_input[4] = {1, 2, 3, 4};
  const std::int8_t conv_weights[2] = {1, 2};
  const std::int32_t conv_bias[1] = {0};
  if (turbovla_conv1x1_int8(conv_input, conv_weights, conv_bias, conv_output, 2,
                            2, 1, 1.0f, false) != 0) {
    return 3;
  }
  if (!check_equal(conv_output, conv_expected, 2, "conv1x1")) {
    return 4;
  }

  if (turbovla_gemm_int8(a, b, bias, output, 0, 2, 3, 1.0f, false) != 1) {
    return 5;
  }
  std::cout << "gemm/conv C simulation passed\n";
  return 0;
}
