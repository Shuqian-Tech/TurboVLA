#pragma once

#include <cstddef>
#include <cstdint>

namespace turbovla {
namespace hls {
namespace e2e {

constexpr std::uint32_t kArenaMagic = 0x54564c41U;
constexpr std::uint32_t kModelMagic = 0x54564d44U;
constexpr std::uint32_t kContractVersion = 0x00020000U;

constexpr std::size_t kHeaderOffset = 0;
constexpr std::size_t kImageOffset = 64;
constexpr std::size_t kImageBytes = 3U * 128U * 128U;
constexpr std::size_t kStateOffset = 49216;
constexpr std::size_t kStateBytes = 8U * sizeof(std::int16_t);
constexpr std::size_t kModelOffset = 49280;
constexpr std::size_t kModelBytes = 150656;
constexpr std::size_t kActionOffset = 199936;
constexpr std::size_t kActionValues = 12U * 7U;
constexpr std::size_t kActionBytes = kActionValues * sizeof(float);
constexpr std::size_t kArenaBytes = 200320;

constexpr std::size_t kHeaderMagic = 0;
constexpr std::size_t kHeaderContractVersion = 4;
constexpr std::size_t kHeaderFrameSequence = 8;
constexpr std::size_t kHeaderInstructionId = 12;
constexpr std::size_t kHeaderCompletedSequence = 16;
constexpr std::size_t kHeaderErrorCode = 20;
constexpr std::size_t kHeaderHardwareVersion = 24;

enum class ErrorCode : std::uint32_t {
  kNone = 0,
  kInvalidInstructionId = 1,
  kInvalidBuffer = 2,
  kDmaTimeout = 3,
  kKernelFault = 4,
  kContractMismatch = 5,
};

int run(std::uint8_t* arena);

}  // namespace e2e
}  // namespace hls
}  // namespace turbovla

int turbovla_lite_e2e(std::uint8_t* arena);
