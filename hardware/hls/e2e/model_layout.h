#pragma once

#include <cstddef>

namespace turbovla {
namespace hls {
namespace e2e {
namespace model {

constexpr std::size_t kMagic = 0;
constexpr std::size_t kContractVersion = 4;
constexpr std::size_t kTotalBytes = 8;

constexpr std::size_t kImageScale = 16;
constexpr std::size_t kConvScale = 20;
constexpr std::size_t kVisualScale = 24;
constexpr std::size_t kLanguageScale = 28;
constexpr std::size_t kFusion0Scale = 32;
constexpr std::size_t kFusion1Scale = 36;
constexpr std::size_t kStateScale = 40;
constexpr std::size_t kHiddenScale = 44;

constexpr std::size_t kConvWeightScale = 48;
constexpr std::size_t kVisualWeightScale = 52;
constexpr std::size_t kFusionVisualWeightScale = 56;
constexpr std::size_t kFusionLanguageWeightScale = 60;
constexpr std::size_t kFusionGateWeightScale = 64;
constexpr std::size_t kStateWeightScale = 68;
constexpr std::size_t kActionInputWeightScale = 72;
constexpr std::size_t kActionOutputWeightScale = 76;
constexpr std::size_t kStateInputScale = 80;

constexpr std::size_t kTensorBase = 128;
constexpr std::size_t kConvWeight = kTensorBase + 0;
constexpr std::size_t kConvBias = kTensorBase + 64;
constexpr std::size_t kVisualProjection = kTensorBase + 128;
constexpr std::size_t kVisualBias = kTensorBase + 2176;
constexpr std::size_t kInstructionTable = kTensorBase + 2688;
constexpr std::size_t kStateProjection = kTensorBase + 35456;
constexpr std::size_t kStateBias = kTensorBase + 36480;
constexpr std::size_t kActionInput = kTensorBase + 36992;
constexpr std::size_t kActionInputBias = kTensorBase + 45184;
constexpr std::size_t kActionOutput = kTensorBase + 45440;
constexpr std::size_t kActionOutputBias = kTensorBase + 50816;
constexpr std::size_t kFusionVisual0 = kTensorBase + 51200;
constexpr std::size_t kFusionLanguage0 = kTensorBase + 67584;
constexpr std::size_t kFusionGate0 = kTensorBase + 83968;
constexpr std::size_t kFusionBias0 = kTensorBase + 100352;
constexpr std::size_t kFusionVisual1 = kTensorBase + 100864;
constexpr std::size_t kFusionLanguage1 = kTensorBase + 117248;
constexpr std::size_t kFusionGate1 = kTensorBase + 133632;
constexpr std::size_t kFusionBias1 = kTensorBase + 150016;

}  // namespace model
}  // namespace e2e
}  // namespace hls
}  // namespace turbovla
