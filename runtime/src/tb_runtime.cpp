#include "turbovla_runtime.hpp"

#include <array>
#include <cstddef>
#include <cstdint>
#include <cstring>
#include <iostream>
#include <utility>
#include <vector>

namespace {

using turbovla::runtime::kActionOffset;
using turbovla::runtime::kActionValues;
using turbovla::runtime::kArenaBytes;
using turbovla::runtime::kContractVersion;
using turbovla::runtime::kControlOffset;
using turbovla::runtime::kModelBytes;
using turbovla::runtime::kModelMagic;
using turbovla::runtime::kModelStateInputScaleOffset;

void write_u32(std::uint8_t* data, std::size_t offset, std::uint32_t value) {
  std::memcpy(data + offset, &value, sizeof(value));
}

void write_float(std::uint8_t* data, std::size_t offset, float value) {
  std::memcpy(data + offset, &value, sizeof(value));
}

class FakeCache final : public turbovla::runtime::CacheMaintenance {
 public:
  void flush(std::size_t offset, std::size_t bytes) override { flushes.emplace_back(offset, bytes); }
  void invalidate(std::size_t offset, std::size_t bytes) override { invalidates.emplace_back(offset, bytes); }

  std::vector<std::pair<std::size_t, std::size_t>> flushes;
  std::vector<std::pair<std::size_t, std::size_t>> invalidates;
};

class FakeRegisters final : public turbovla::runtime::RegisterIo {
 public:
  explicit FakeRegisters(std::uint8_t* arena) : arena_(arena) {}

  std::uint32_t read32(std::uint32_t offset) override {
    if (offset == kControlOffset && start_seen_ && completes) {
      return (1U << 1U) | (1U << 3U);
    }
    return registers_[offset / 4U];
  }

  void write32(std::uint32_t offset, std::uint32_t value) override {
    registers_[offset / 4U] = value;
    if (offset == kControlOffset && (value & 1U) != 0U) {
      start_seen_ = true;
      if (completes) {
        std::uint32_t sequence = 0;
        std::memcpy(&sequence, arena_ + 8, sizeof(sequence));
        write_u32(arena_, 16, sequence);
        write_u32(arena_, 20, kernel_error);
        write_u32(arena_, 24, hardware_version);
        for (std::size_t index = 0; index < kActionValues; ++index) {
          const float value_out = static_cast<float>(index) / 100.0f;
          std::memcpy(arena_ + kActionOffset + index * sizeof(float), &value_out, sizeof(value_out));
        }
      }
    }
  }

  bool completes = true;
  std::uint32_t kernel_error = 0;
  std::uint32_t hardware_version = kContractVersion;
  std::array<std::uint32_t, 16> registers_{};

 private:
  std::uint8_t* arena_;
  bool start_seen_ = false;
};

std::vector<std::uint8_t> valid_model() {
  std::vector<std::uint8_t> model(kModelBytes);
  write_u32(model.data(), 0, kModelMagic);
  write_u32(model.data(), 4, kContractVersion);
  write_u32(model.data(), 8, kModelBytes);
  write_float(model.data(), kModelStateInputScaleOffset, 0.025f);
  return model;
}

}  // namespace

int main() {
  alignas(64) std::array<std::uint8_t, kArenaBytes> arena{};
  FakeCache cache;
  FakeRegisters registers(arena.data());
  turbovla::runtime::ArenaBuffer buffer{arena.data(), 0x0000001080000000ULL, arena.size()};
  turbovla::runtime::PlArenaExecutor device(buffer, registers, cache);
  const auto model = valid_model();

  turbovla::runtime::PlArenaExecutor invalid_device(
      {arena.data(), 0, arena.size()}, registers, cache);
  if (invalid_device.load_model(model.data(), model.size()) !=
      turbovla::runtime::ErrorCode::kInvalidBuffer) {
    return 1;
  }

  auto v2_model = model;
  write_u32(v2_model.data(), 4, 0x00020000U);
  if (device.load_model(v2_model.data(), v2_model.size()) !=
      turbovla::runtime::ErrorCode::kContractMismatch) {
    return 2;
  }

  auto invalid_scale_model = model;
  write_float(invalid_scale_model.data(), kModelStateInputScaleOffset, 0.0f);
  if (device.load_model(invalid_scale_model.data(), invalid_scale_model.size()) !=
      turbovla::runtime::ErrorCode::kContractMismatch) {
    return 3;
  }

  auto nonfinite_scale_model = model;
  write_u32(nonfinite_scale_model.data(), kModelStateInputScaleOffset, 0x7f800000U);
  if (device.load_model(nonfinite_scale_model.data(), nonfinite_scale_model.size()) !=
      turbovla::runtime::ErrorCode::kContractMismatch) {
    return 4;
  }

  if (device.load_model(model.data(), model.size()) != turbovla::runtime::ErrorCode::kNone) {
    return 5;
  }
  turbovla::runtime::TurboVlaRuntime runtime(
      {}, [&device](const auto& input, auto& output, std::uint32_t timeout) {
        return device.run(input, output, timeout);
      });
  turbovla::runtime::FrameInput input;
  input.state[0] = -123;
  input.instruction_id = 7;
  turbovla::runtime::ActionOutput output;
  if (runtime.run(input, output) != turbovla::runtime::ErrorCode::kNone || output.action[83] != 0.83f) {
    return 6;
  }
  if (registers.registers_[turbovla::runtime::kArenaAddressLowOffset / 4U] != 0x80000000U ||
      registers.registers_[turbovla::runtime::kArenaAddressHighOffset / 4U] != 0x10U) {
    return 7;
  }
  if (cache.flushes.size() != 4 || cache.invalidates.size() != 2) {
    return 8;
  }

  input.instruction_id = 256;
  if (runtime.run(input, output) != turbovla::runtime::ErrorCode::kInvalidInstructionId) {
    return 9;
  }

  alignas(64) std::array<std::uint8_t, kArenaBytes> timeout_arena{};
  FakeCache timeout_cache;
  FakeRegisters timeout_registers(timeout_arena.data());
  timeout_registers.completes = false;
  turbovla::runtime::PlArenaExecutor timeout_device(
      {timeout_arena.data(), 0x90000000ULL, timeout_arena.size()}, timeout_registers, timeout_cache);
  if (timeout_device.load_model(model.data(), model.size()) != turbovla::runtime::ErrorCode::kNone) {
    return 10;
  }
  input.instruction_id = 0;
  if (timeout_device.run(input, output, 2) != turbovla::runtime::ErrorCode::kDmaTimeout) {
    return 11;
  }

  std::cout << "runtime arena/MMIO/cache path passed\n";
  return 0;
}
