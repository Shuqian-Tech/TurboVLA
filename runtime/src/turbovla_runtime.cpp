#include "turbovla_runtime.hpp"

#include <algorithm>
#include <utility>

namespace turbovla::runtime {
namespace {
constexpr std::uint32_t kStatusOffset = 0x04;
constexpr std::uint32_t kErrorOffset = 0x08;
constexpr std::uint32_t kVersionOffset = 0x0C;
constexpr std::uint32_t kControlOffset = 0x00;
constexpr std::uint32_t kErrorClearOffset = 0x38;
constexpr std::uint32_t kIdleBit = 1U << 0;
constexpr std::uint32_t kBusyBit = 1U << 1;
constexpr std::uint32_t kDoneBit = 1U << 2;
constexpr std::uint32_t kErrorBit = 1U << 3;
}

std::uint32_t RegisterModel::read(std::uint32_t offset) const {
  if (offset % 4U != 0U || offset / 4U >= registers_.size()) {
    return 0;
  }
  return registers_[offset / 4U];
}

void RegisterModel::write(std::uint32_t offset, std::uint32_t value) {
  if (offset % 4U != 0U || offset / 4U >= registers_.size()) {
    return;
  }
  registers_[offset / 4U] = value;
}

void RegisterModel::reset() {
  registers_.fill(0);
  write(kStatusOffset, kIdleBit);
}

TurboVlaRuntime::TurboVlaRuntime(RuntimeConfig config, PlExecutor executor)
    : config_(config), executor_(std::move(executor)) {
  registers_.reset();
  registers_.write(kVersionOffset, hardware_contract_version_);
}

void TurboVlaRuntime::set_hardware_contract_version(std::uint32_t version) {
  hardware_contract_version_ = version;
  registers_.write(kVersionOffset, version);
}

bool TurboVlaRuntime::validate_input(const FrameInput& input) {
  if (input.instruction_id >= config_.instruction_table_size) {
    last_error_ = ErrorCode::kInvalidInstructionId;
    return false;
  }
  if (hardware_contract_version_ != config_.expected_contract_version) {
    last_error_ = ErrorCode::kContractMismatch;
    return false;
  }
  return true;
}

ErrorCode TurboVlaRuntime::run(const FrameInput& input, ActionOutput& output) {
  if (!validate_input(input) || executor_ == nullptr) {
    if (executor_ == nullptr) {
      last_error_ = ErrorCode::kKernelFault;
    }
    registers_.write(kErrorOffset, static_cast<std::uint32_t>(last_error_));
    registers_.write(kStatusOffset, kErrorBit);
    return last_error_;
  }
  if ((registers_.read(kStatusOffset) & kIdleBit) == 0U) {
    last_error_ = ErrorCode::kDmaTimeout;
    registers_.write(kErrorOffset, static_cast<std::uint32_t>(last_error_));
    registers_.write(kStatusOffset, kErrorBit);
    return last_error_;
  }
  registers_.write(kControlOffset, 1U);
  registers_.write(kStatusOffset, kBusyBit);
  if (!executor_(input, output, config_.timeout_ticks)) {
    last_error_ = ErrorCode::kDmaTimeout;
    registers_.write(kErrorOffset, static_cast<std::uint32_t>(last_error_));
    registers_.write(kStatusOffset, kErrorBit);
    return last_error_;
  }
  last_error_ = ErrorCode::kNone;
  registers_.write(kErrorOffset, 0U);
  registers_.write(kStatusOffset, kIdleBit | kDoneBit);
  return last_error_;
}

}  // namespace turbovla::runtime
