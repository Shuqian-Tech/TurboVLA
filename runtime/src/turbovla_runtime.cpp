#include "turbovla_runtime.hpp"

#include <cmath>
#include <cstring>
#include <utility>

namespace turbovla::runtime {
namespace {

constexpr std::size_t kHeaderMagic = 0;
constexpr std::size_t kHeaderContractVersion = 4;
constexpr std::size_t kHeaderFrameSequence = 8;
constexpr std::size_t kHeaderInstructionId = 12;
constexpr std::size_t kHeaderCompletedSequence = 16;
constexpr std::size_t kHeaderErrorCode = 20;
constexpr std::size_t kHeaderHardwareVersion = 24;
constexpr std::uint32_t kStart = 1U << 0U;
constexpr std::uint32_t kDone = 1U << 1U;
constexpr std::uint32_t kInterruptEnable = 1U;
constexpr std::uint32_t kInterruptStatusMask = 0x3U;

std::uint32_t read_u32(const std::uint8_t* data, std::size_t offset) {
  std::uint32_t value = 0;
  std::memcpy(&value, data + offset, sizeof(value));
  return value;
}

float read_float(const std::uint8_t* data, std::size_t offset) {
  float value = 0.0f;
  std::memcpy(&value, data + offset, sizeof(value));
  return value;
}

void write_u16(std::uint8_t* data, std::size_t offset, std::uint16_t value) {
  std::memcpy(data + offset, &value, sizeof(value));
}

void write_u32(std::uint8_t* data, std::size_t offset, std::uint32_t value) {
  std::memcpy(data + offset, &value, sizeof(value));
}

bool valid_arena(const ArenaBuffer& arena) {
  return arena.data != nullptr && arena.bytes >= kArenaBytes && arena.physical_address != 0 &&
         reinterpret_cast<std::uintptr_t>(arena.data) % 64U == 0U && arena.physical_address % 64U == 0U;
}

ErrorCode decode_error(std::uint32_t value) {
  if (value <= static_cast<std::uint32_t>(ErrorCode::kContractMismatch)) {
    return static_cast<ErrorCode>(value);
  }
  return ErrorCode::kKernelFault;
}

}  // namespace

VolatileRegisterIo::VolatileRegisterIo(volatile std::uint32_t* registers, std::size_t register_words)
    : registers_(registers), register_words_(register_words) {}

std::uint32_t VolatileRegisterIo::read32(std::uint32_t offset) {
  if (registers_ == nullptr || offset % sizeof(std::uint32_t) != 0 ||
      offset / sizeof(std::uint32_t) >= register_words_) {
    return 0;
  }
  return registers_[offset / sizeof(std::uint32_t)];
}

void VolatileRegisterIo::write32(std::uint32_t offset, std::uint32_t value) {
  if (registers_ != nullptr && offset % sizeof(std::uint32_t) == 0 &&
      offset / sizeof(std::uint32_t) < register_words_) {
    registers_[offset / sizeof(std::uint32_t)] = value;
  }
}

PlArenaExecutor::PlArenaExecutor(ArenaBuffer arena, RegisterIo& registers, CacheMaintenance& cache)
    : arena_(arena), registers_(registers), cache_(cache) {}

ErrorCode PlArenaExecutor::load_model(const std::uint8_t* model, std::size_t bytes) {
  if (!valid_arena(arena_) || model == nullptr) {
    return ErrorCode::kInvalidBuffer;
  }
  if (bytes != kModelBytes || read_u32(model, 0) != kModelMagic ||
      read_u32(model, 4) != kContractVersion || read_u32(model, 8) != kModelBytes ||
      !std::isfinite(read_float(model, kModelStateInputScaleOffset)) ||
      read_float(model, kModelStateInputScaleOffset) <= 0.0f) {
    return ErrorCode::kContractMismatch;
  }
  std::memcpy(arena_.data + kModelOffset, model, bytes);
  cache_.flush(kModelOffset, kModelBytes);
  model_loaded_ = true;
  return ErrorCode::kNone;
}

ErrorCode PlArenaExecutor::reset_control() {
  if (!valid_arena(arena_)) {
    return ErrorCode::kInvalidBuffer;
  }
  registers_.write32(kControlOffset, 0);
  registers_.write32(kInterruptEnableOffset, 0);
  registers_.write32(kGlobalInterruptOffset, 0);
  const std::uint32_t pending = registers_.read32(kInterruptStatusOffset) & kInterruptStatusMask;
  if (pending != 0U) {
    registers_.write32(kInterruptStatusOffset, pending);
  }
  return ErrorCode::kNone;
}

ErrorCode PlArenaExecutor::run(const FrameInput& input, ActionOutput& output, std::uint32_t timeout_ticks) {
  if (!valid_arena(arena_) || !model_loaded_) {
    return ErrorCode::kInvalidBuffer;
  }
  if (timeout_ticks == 0) {
    return ErrorCode::kDmaTimeout;
  }
  if (reset_control() != ErrorCode::kNone) {
    return ErrorCode::kInvalidBuffer;
  }
  last_interrupt_status_ = 0;
  ++frame_sequence_;
  write_u32(arena_.data, kHeaderMagic, kArenaMagic);
  write_u32(arena_.data, kHeaderContractVersion, kContractVersion);
  write_u32(arena_.data, kHeaderFrameSequence, frame_sequence_);
  write_u16(arena_.data, kHeaderInstructionId, input.instruction_id);
  write_u32(arena_.data, kHeaderCompletedSequence, 0);
  write_u32(arena_.data, kHeaderErrorCode, 0);
  write_u32(arena_.data, kHeaderHardwareVersion, 0);
  std::memcpy(arena_.data + kImageOffset, input.image.data(), input.image.size());
  std::memcpy(arena_.data + kStateOffset, input.state.data(), input.state.size() * sizeof(std::int16_t));

  cache_.flush(kHeaderOffset, 64);
  cache_.flush(kImageOffset, kImageBytes);
  cache_.flush(kStateOffset, kStateValues * sizeof(std::int16_t));
  registers_.write32(kArenaAddressLowOffset, static_cast<std::uint32_t>(arena_.physical_address));
  registers_.write32(kArenaAddressHighOffset, static_cast<std::uint32_t>(arena_.physical_address >> 32U));
  registers_.write32(kGlobalInterruptOffset, kInterruptEnable);
  registers_.write32(kInterruptEnableOffset, kInterruptEnable);
  registers_.write32(kControlOffset, kStart);

  bool completed = false;
  for (std::uint32_t tick = 0; tick < timeout_ticks; ++tick) {
    const std::uint32_t control = registers_.read32(kControlOffset);
    if ((control & kDone) != 0U) {
      completed = true;
      break;
    }
  }
  if (!completed) {
    reset_control();
    return ErrorCode::kDmaTimeout;
  }
  last_interrupt_status_ = registers_.read32(kInterruptStatusOffset) & kInterruptStatusMask;
  reset_control();
  cache_.invalidate(kHeaderOffset, 64);
  cache_.invalidate(kActionOffset, kActionValues * sizeof(float));

  const auto error = decode_error(read_u32(arena_.data, kHeaderErrorCode));
  const auto kernel_return = decode_error(registers_.read32(kKernelReturnOffset));
  if (error != ErrorCode::kNone) {
    return error;
  }
  if (kernel_return != ErrorCode::kNone) {
    return kernel_return;
  }
  if (read_u32(arena_.data, kHeaderHardwareVersion) != kContractVersion) {
    return ErrorCode::kContractMismatch;
  }
  if (read_u32(arena_.data, kHeaderMagic) != kArenaMagic ||
      read_u32(arena_.data, kHeaderContractVersion) != kContractVersion) {
    return ErrorCode::kKernelFault;
  }
  if (read_u32(arena_.data, kHeaderCompletedSequence) != frame_sequence_) {
    return ErrorCode::kKernelFault;
  }
  ActionOutput candidate;
  std::memcpy(candidate.action.data(), arena_.data + kActionOffset, kActionValues * sizeof(float));
  for (const float value : candidate.action) {
    if (!std::isfinite(value)) {
      return ErrorCode::kKernelFault;
    }
  }
  output = candidate;
  return ErrorCode::kNone;
}

TurboVlaRuntime::TurboVlaRuntime(RuntimeConfig config, PlExecutor executor)
    : config_(config), executor_(std::move(executor)) {}

ErrorCode TurboVlaRuntime::run(const FrameInput& input, ActionOutput& output) {
  if (input.instruction_id >= config_.instruction_table_size) {
    last_error_ = ErrorCode::kInvalidInstructionId;
  } else if (config_.expected_contract_version != kContractVersion) {
    last_error_ = ErrorCode::kContractMismatch;
  } else if (executor_ == nullptr) {
    last_error_ = ErrorCode::kKernelFault;
  } else {
    last_error_ = executor_(input, output, config_.timeout_ticks);
  }
  return last_error_;
}

}  // namespace turbovla::runtime
