#pragma once

#include <array>
#include <cstdint>
#include <functional>
#include <vector>

namespace turbovla::runtime {

constexpr std::uint32_t kContractVersion = 0x00010000;
constexpr std::size_t kImageBytes = 1U * 1U * 3U * 128U * 128U;
constexpr std::size_t kStateValues = 8U;
constexpr std::size_t kActionValues = 12U * 7U;

enum class ErrorCode : std::uint32_t {
  kNone = 0,
  kInvalidInstructionId = 1,
  kInvalidBuffer = 2,
  kDmaTimeout = 3,
  kKernelFault = 4,
  kContractMismatch = 5,
};

struct FrameInput {
  std::array<std::uint8_t, kImageBytes> image{};
  std::array<std::int16_t, kStateValues> state{};
  std::uint16_t instruction_id = 0;
};

struct ActionOutput {
  std::array<float, kActionValues> action{};
};

struct RuntimeConfig {
  std::uint32_t expected_contract_version = kContractVersion;
  std::uint32_t timeout_ticks = 1000;
  std::uint16_t instruction_table_size = 256;
};

class RegisterModel {
 public:
  std::uint32_t read(std::uint32_t offset) const;
  void write(std::uint32_t offset, std::uint32_t value);
  void reset();

 private:
  std::array<std::uint32_t, 15> registers_{};
};

using PlExecutor = std::function<bool(const FrameInput&, ActionOutput&, std::uint32_t timeout_ticks)>;

class TurboVlaRuntime {
 public:
  TurboVlaRuntime(RuntimeConfig config, PlExecutor executor);

  ErrorCode run(const FrameInput& input, ActionOutput& output);
  void set_hardware_contract_version(std::uint32_t version);
  const RegisterModel& registers() const { return registers_; }
  ErrorCode last_error() const { return last_error_; }

 private:
  bool validate_input(const FrameInput& input);
  RuntimeConfig config_;
  PlExecutor executor_;
  RegisterModel registers_;
  ErrorCode last_error_ = ErrorCode::kNone;
  std::uint32_t hardware_contract_version_ = kContractVersion;
};

}  // namespace turbovla::runtime

