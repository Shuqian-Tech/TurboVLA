#pragma once

#include <array>
#include <cstddef>
#include <cstdint>
#include <functional>

namespace turbovla::runtime {

constexpr std::uint32_t kArenaMagic = 0x54564c41U;
constexpr std::uint32_t kModelMagic = 0x54564d44U;
constexpr std::uint32_t kContractVersion = 0x00020000U;
constexpr std::size_t kImageBytes = 3U * 128U * 128U;
constexpr std::size_t kStateValues = 8U;
constexpr std::size_t kActionValues = 12U * 7U;
constexpr std::size_t kHeaderOffset = 0;
constexpr std::size_t kImageOffset = 64;
constexpr std::size_t kStateOffset = 49216;
constexpr std::size_t kModelOffset = 49280;
constexpr std::size_t kModelBytes = 150656;
constexpr std::size_t kActionOffset = 199936;
constexpr std::size_t kArenaBytes = 200320;

constexpr std::uint32_t kControlOffset = 0x00;
constexpr std::uint32_t kGlobalInterruptOffset = 0x04;
constexpr std::uint32_t kInterruptEnableOffset = 0x08;
constexpr std::uint32_t kInterruptStatusOffset = 0x0C;
constexpr std::uint32_t kArenaAddressLowOffset = 0x10;
constexpr std::uint32_t kArenaAddressHighOffset = 0x14;

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

class RegisterIo {
 public:
  virtual ~RegisterIo() = default;
  virtual std::uint32_t read32(std::uint32_t offset) = 0;
  virtual void write32(std::uint32_t offset, std::uint32_t value) = 0;
};

class CacheMaintenance {
 public:
  virtual ~CacheMaintenance() = default;
  virtual void flush(std::size_t offset, std::size_t bytes) = 0;
  virtual void invalidate(std::size_t offset, std::size_t bytes) = 0;
};

struct ArenaBuffer {
  std::uint8_t* data = nullptr;
  std::uint64_t physical_address = 0;
  std::size_t bytes = 0;
};

class VolatileRegisterIo final : public RegisterIo {
 public:
  VolatileRegisterIo(volatile std::uint32_t* registers, std::size_t register_words);
  std::uint32_t read32(std::uint32_t offset) override;
  void write32(std::uint32_t offset, std::uint32_t value) override;

 private:
  volatile std::uint32_t* registers_;
  std::size_t register_words_;
};

class PlArenaExecutor {
 public:
  PlArenaExecutor(ArenaBuffer arena, RegisterIo& registers, CacheMaintenance& cache);

  ErrorCode load_model(const std::uint8_t* model, std::size_t bytes);
  ErrorCode run(const FrameInput& input, ActionOutput& output, std::uint32_t timeout_ticks);

 private:
  ArenaBuffer arena_;
  RegisterIo& registers_;
  CacheMaintenance& cache_;
  std::uint32_t frame_sequence_ = 0;
  bool model_loaded_ = false;
};

using PlExecutor = std::function<ErrorCode(const FrameInput&, ActionOutput&, std::uint32_t timeout_ticks)>;

class TurboVlaRuntime {
 public:
  TurboVlaRuntime(RuntimeConfig config, PlExecutor executor);

  ErrorCode run(const FrameInput& input, ActionOutput& output);
  ErrorCode last_error() const { return last_error_; }

 private:
  RuntimeConfig config_;
  PlExecutor executor_;
  ErrorCode last_error_ = ErrorCode::kNone;
};

}  // namespace turbovla::runtime
