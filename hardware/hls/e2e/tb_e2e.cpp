#include "e2e.h"

#include <algorithm>
#include <cmath>
#include <cstdint>
#include <fstream>
#include <iostream>
#include <stdexcept>
#include <string>
#include <vector>

namespace {

std::vector<std::uint8_t> read_file(const std::string& path) {
  std::ifstream stream(path, std::ios::binary | std::ios::ate);
  if (!stream) {
    throw std::runtime_error("cannot open " + path);
  }
  const auto size = stream.tellg();
  std::vector<std::uint8_t> data(static_cast<std::size_t>(size));
  stream.seekg(0);
  stream.read(reinterpret_cast<char*>(data.data()), size);
  return data;
}

void write_u16(std::uint8_t* data, std::size_t offset, std::uint16_t value) {
  data[offset] = static_cast<std::uint8_t>(value);
  data[offset + 1] = static_cast<std::uint8_t>(value >> 8U);
}

void write_u32(std::uint8_t* data, std::size_t offset, std::uint32_t value) {
  for (int byte = 0; byte < 4; ++byte) {
    data[offset + byte] = static_cast<std::uint8_t>(value >> (byte * 8));
  }
}

std::uint32_t read_u32(const std::uint8_t* data, std::size_t offset) {
  std::uint32_t value = 0;
  for (int byte = 0; byte < 4; ++byte) {
    value |= static_cast<std::uint32_t>(data[offset + byte]) << (byte * 8);
  }
  return value;
}

float read_float(const std::uint8_t* data) {
  union FloatBits {
    std::uint32_t bits;
    float value;
  } converted{};
  converted.bits = static_cast<std::uint32_t>(data[0]) |
                   (static_cast<std::uint32_t>(data[1]) << 8U) |
                   (static_cast<std::uint32_t>(data[2]) << 16U) |
                   (static_cast<std::uint32_t>(data[3]) << 24U);
  return converted.value;
}

}  // namespace

int main(int argc, char** argv) {
  if (argc != 2) {
    std::cerr << "usage: tb_e2e <fixture-dir>\n";
    return 2;
  }
  const std::string root = argv[1];
  const auto image = read_file(root + "/image.bin");
  const auto state = read_file(root + "/state.bin");
  const auto instruction = read_file(root + "/instruction_id.bin");
  const auto model = read_file(root + "/model.bin");
  const auto expected_bytes = read_file(root + "/action.bin");
  if (image.size() != turbovla::hls::e2e::kImageBytes ||
      state.size() != turbovla::hls::e2e::kStateBytes ||
      model.size() != turbovla::hls::e2e::kModelBytes ||
      expected_bytes.size() != turbovla::hls::e2e::kActionBytes || instruction.size() != 2) {
    std::cerr << "fixture size mismatch\n";
    return 3;
  }

  std::vector<turbovla::hls::e2e::ArenaWord> arena(turbovla::hls::e2e::kArenaWords);
  auto* arena_bytes = reinterpret_cast<std::uint8_t*>(arena.data());
  write_u32(arena_bytes, turbovla::hls::e2e::kHeaderMagic, turbovla::hls::e2e::kArenaMagic);
  write_u32(arena_bytes, turbovla::hls::e2e::kHeaderContractVersion,
            turbovla::hls::e2e::kContractVersion);
  write_u32(arena_bytes, turbovla::hls::e2e::kHeaderFrameSequence, 17);
  write_u16(arena_bytes, turbovla::hls::e2e::kHeaderInstructionId,
            static_cast<std::uint16_t>(instruction[0] | (instruction[1] << 8U)));
  std::copy(image.begin(), image.end(), arena_bytes + turbovla::hls::e2e::kImageOffset);
  std::copy(state.begin(), state.end(), arena_bytes + turbovla::hls::e2e::kStateOffset);
  std::copy(model.begin(), model.end(), arena_bytes + turbovla::hls::e2e::kModelOffset);

  if (turbovla_lite_e2e(arena.data()) != 0 ||
      read_u32(arena_bytes, turbovla::hls::e2e::kHeaderCompletedSequence) != 17 ||
      read_u32(arena_bytes, turbovla::hls::e2e::kHeaderErrorCode) != 0) {
    std::cerr << "kernel status mismatch\n";
    return 4;
  }

  float max_error = 0.0f;
  float total_error = 0.0f;
  for (std::size_t index = 0; index < turbovla::hls::e2e::kActionValues; ++index) {
    const float actual =
        read_float(arena_bytes + turbovla::hls::e2e::kActionOffset + index * sizeof(float));
    const float expected = read_float(expected_bytes.data() + index * sizeof(float));
    const float error = std::abs(actual - expected);
    max_error = std::max(max_error, error);
    total_error += error;
  }
  const float mean_error = total_error / static_cast<float>(turbovla::hls::e2e::kActionValues);
  std::cout << "e2e action parity max_abs_error=" << max_error << " mean_abs_error=" << mean_error << '\n';
  if (max_error > 1.0e-5f || mean_error > 1.0e-6f) {
    return 5;
  }

  write_u16(arena_bytes, turbovla::hls::e2e::kHeaderInstructionId, 65535);
  if (turbovla_lite_e2e(arena.data()) != static_cast<int>(turbovla::hls::e2e::ErrorCode::kInvalidInstructionId)) {
    return 6;
  }
  std::cout << "e2e invalid-instruction gate passed\n";
  return 0;
}
