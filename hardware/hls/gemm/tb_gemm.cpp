#include "gemm.h"

#include <array>
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
  constexpr std::array<std::int8_t, 6> a{1, -2, 3, 4, 5, -6};
  constexpr std::array<std::int8_t, 6> b{2, 1, -1, 3, 4, -2};
  constexpr std::array<std::int32_t, 2> bias{1, -3};
  std::array<std::int8_t, 4> output{};
  constexpr std::array<std::int8_t, 4> expected{17, -14, -20, 28};
  if (turbovla::hls::gemm_int8(a.data(), b.data(), bias.data(), output.data(), 2, 2, 3, 1.0f, false) !=
      turbovla::hls::GemmStatus::kOk) {
    return 1;
  }
  if (!check_equal(output.data(), expected.data(), 4, "gemm")) {
    return 2;
  }

  std::array<std::int8_t, 2> conv_output{};
  constexpr std::array<std::int8_t, 2> conv_expected{5, 11};
  constexpr std::array<std::int8_t, 4> conv_input{1, 2, 3, 4};
  constexpr std::array<std::int8_t, 2> conv_weights{1, 2};
  constexpr std::array<std::int32_t, 1> conv_bias{0};
  if (turbovla::hls::conv1x1_int8(conv_input.data(), conv_weights.data(), conv_bias.data(), conv_output.data(), 2,
                                  2, 1, 1.0f, false) != turbovla::hls::GemmStatus::kOk) {
    return 3;
  }
  if (!check_equal(conv_output.data(), conv_expected.data(), 2, "conv1x1")) {
    return 4;
  }

  if (turbovla::hls::gemm_int8(a.data(), b.data(), bias.data(), output.data(), 0, 2, 3, 1.0f, false) !=
      turbovla::hls::GemmStatus::kInvalidShape) {
    return 5;
  }
  std::cout << "gemm/conv C simulation passed\n";
  return 0;
}
