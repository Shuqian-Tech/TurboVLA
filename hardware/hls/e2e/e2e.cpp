#include "e2e.h"

#include "model_layout.h"

#include <cmath>

namespace turbovla {
namespace hls {
namespace e2e {
namespace {

constexpr int kImageHeight = 128;
constexpr int kImageWidth = 128;
constexpr int kConvChannels = 16;
constexpr int kTokenRows = 4;
constexpr int kTokenCols = 8;
constexpr int kTokens = kTokenRows * kTokenCols;
constexpr int kHidden = 128;
constexpr int kState = 8;
constexpr int kActionHidden = 64;
constexpr int kInstructions = 256;
constexpr float kStateNormalization = 1.0f / 1024.0f;
constexpr float kMean[3] = {0.485f, 0.456f, 0.406f};
constexpr float kStd[3] = {0.229f, 0.224f, 0.225f};

std::uint8_t read_u8(const ArenaWord* data, std::size_t offset) {
  const ArenaWord word = data[offset / sizeof(ArenaWord)];
  return static_cast<std::uint8_t>(word >> ((offset % sizeof(ArenaWord)) * 8U));
}

std::uint16_t read_u16(const ArenaWord* data, std::size_t offset) {
  return static_cast<std::uint16_t>(read_u8(data, offset)) |
         (static_cast<std::uint16_t>(read_u8(data, offset + 1)) << 8U);
}

std::int16_t read_i16(const ArenaWord* data, std::size_t offset) {
  return static_cast<std::int16_t>(read_u16(data, offset));
}

ArenaWord read_u32(const ArenaWord* data, std::size_t offset) {
  return data[offset / sizeof(ArenaWord)];
}

void write_u32(ArenaWord* data, std::size_t offset, ArenaWord value) {
  data[offset / sizeof(ArenaWord)] = value;
}

float read_float(const ArenaWord* data, std::size_t offset) {
  union FloatBits {
    std::uint32_t bits;
    float value;
  } converted{};
  converted.bits = read_u32(data, offset);
  return converted.value;
}

void write_float(ArenaWord* data, std::size_t offset, float value) {
  union FloatBits {
    std::uint32_t bits;
    float value;
  } converted{};
  converted.value = value;
  write_u32(data, offset, converted.bits);
}

std::int8_t read_i8(const ArenaWord* data, std::size_t offset) {
  return static_cast<std::int8_t>(read_u8(data, offset));
}

std::int8_t quantize(float value, float scale) {
  float rounded = std::round(value / scale);
  if (rounded > 127.0f) {
    rounded = 127.0f;
  } else if (rounded < -128.0f) {
    rounded = -128.0f;
  }
  return static_cast<std::int8_t>(rounded);
}

float sigmoid(float value) {
  const float clipped = value < -12.0f ? -12.0f : (value > 12.0f ? 12.0f : value);
  return 1.0f / (1.0f + std::exp(-clipped));
}

ErrorCode validate(const ArenaWord* arena) {
  if (arena == nullptr) {
    return ErrorCode::kInvalidBuffer;
  }
  if (read_u32(arena, kHeaderMagic) != kArenaMagic ||
      read_u32(arena, kHeaderContractVersion) != kContractVersion) {
    return ErrorCode::kContractMismatch;
  }
  const ArenaWord* packed = arena + kModelOffset / sizeof(ArenaWord);
  if (read_u32(packed, model::kMagic) != kModelMagic ||
      read_u32(packed, model::kContractVersion) != kContractVersion ||
      read_u32(packed, model::kTotalBytes) != kModelBytes ||
      !std::isfinite(read_float(packed, model::kStateInputScale)) ||
      read_float(packed, model::kStateInputScale) <= 0.0f) {
    return ErrorCode::kContractMismatch;
  }
  const std::uint16_t instruction = read_u16(arena, kHeaderInstructionId);
  return instruction < kInstructions ? ErrorCode::kNone : ErrorCode::kInvalidInstructionId;
}

void finish(ArenaWord* arena, ErrorCode error) {
  if (arena == nullptr) {
    return;
  }
  const ArenaWord frame_sequence = read_u32(arena, kHeaderFrameSequence);
  write_u32(arena, kHeaderHardwareVersion, kContractVersion);
  write_u32(arena, kHeaderErrorCode, static_cast<std::uint32_t>(error));
  write_u32(arena, kHeaderCompletedSequence, frame_sequence);
}

void encode_visual(const ArenaWord* arena, const ArenaWord* packed, std::int8_t visual[kTokens][kHidden]) {
  const float image_scale = read_float(packed, model::kImageScale);
  const float conv_scale = read_float(packed, model::kConvScale);
  const float visual_scale = read_float(packed, model::kVisualScale);
  const float conv_weight_scale = read_float(packed, model::kConvWeightScale);
  const float visual_weight_scale = read_float(packed, model::kVisualWeightScale);
  std::int32_t pooled[kTokens][kConvChannels] = {};

  for (int token_row = 0; token_row < kTokenRows; ++token_row) {
    for (int token_col = 0; token_col < kTokenCols; ++token_col) {
      const int token = token_row * kTokenCols + token_col;
      for (int row_in_token = 0; row_in_token < kImageHeight / kTokenRows; ++row_in_token) {
        const int row = token_row * (kImageHeight / kTokenRows) + row_in_token;
        for (int col_in_token = 0; col_in_token < kImageWidth / kTokenCols; ++col_in_token) {
          const int col = token_col * (kImageWidth / kTokenCols) + col_in_token;
          std::int8_t pixel[3];
          for (int channel = 0; channel < 3; ++channel) {
            const std::size_t image_index =
                kImageOffset + channel * kImageHeight * kImageWidth + row * kImageWidth + col;
            const float normalized =
                (static_cast<float>(read_u8(arena, image_index)) / 255.0f - kMean[channel]) / kStd[channel];
            pixel[channel] = quantize(normalized, image_scale);
          }
          for (int output_channel = 0; output_channel < kConvChannels; ++output_channel) {
            std::int32_t accumulator = 0;
            for (int input_channel = 0; input_channel < 3; ++input_channel) {
              accumulator += static_cast<std::int32_t>(pixel[input_channel]) *
                             static_cast<std::int32_t>(
                                 read_i8(packed, model::kConvWeight + output_channel * 3 + input_channel));
            }
            float value = accumulator * image_scale * conv_weight_scale +
                          read_float(packed, model::kConvBias + output_channel * sizeof(float));
            if (value < 0.0f) {
              value = 0.0f;
            }
            pooled[token][output_channel] += quantize(value, conv_scale);
          }
        }
      }
    }
  }

  constexpr int kPixelsPerToken = (kImageHeight / kTokenRows) * (kImageWidth / kTokenCols);
  for (int token = 0; token < kTokens; ++token) {
    for (int output_channel = 0; output_channel < kHidden; ++output_channel) {
      std::int32_t accumulator = 0;
      for (int input_channel = 0; input_channel < kConvChannels; ++input_channel) {
        const std::int8_t pooled_value = static_cast<std::int8_t>(pooled[token][input_channel] / kPixelsPerToken);
        accumulator += static_cast<std::int32_t>(pooled_value) *
                       static_cast<std::int32_t>(read_i8(
                           packed, model::kVisualProjection + input_channel * kHidden + output_channel));
      }
      float value = accumulator * conv_scale * visual_weight_scale +
                    read_float(packed, model::kVisualBias + output_channel * sizeof(float));
      if (value < 0.0f) {
        value = 0.0f;
      }
      visual[token][output_channel] = quantize(value, visual_scale);
    }
  }
}

void fuse_layer(const ArenaWord* packed,
                int layer,
                const std::int8_t language[kHidden],
                const std::int8_t input[kTokens][kHidden],
                std::int8_t output[kTokens][kHidden]) {
  const std::size_t visual_weight = layer == 0 ? model::kFusionVisual0 : model::kFusionVisual1;
  const std::size_t language_weight = layer == 0 ? model::kFusionLanguage0 : model::kFusionLanguage1;
  const std::size_t gate_weight = layer == 0 ? model::kFusionGate0 : model::kFusionGate1;
  const std::size_t bias = layer == 0 ? model::kFusionBias0 : model::kFusionBias1;
  const float input_scale = read_float(packed, layer == 0 ? model::kVisualScale : model::kFusion0Scale);
  const float output_scale = read_float(packed, layer == 0 ? model::kFusion0Scale : model::kFusion1Scale);
  const float language_scale = read_float(packed, model::kLanguageScale);
  const float visual_weight_scale = read_float(packed, model::kFusionVisualWeightScale);
  const float language_weight_scale = read_float(packed, model::kFusionLanguageWeightScale);
  const float gate_weight_scale = read_float(packed, model::kFusionGateWeightScale);
  std::int32_t language_candidate[kHidden] = {};
  std::int32_t language_gate[kHidden] = {};

  for (int output_channel = 0; output_channel < kHidden; ++output_channel) {
    for (int input_channel = 0; input_channel < kHidden; ++input_channel) {
      language_candidate[output_channel] +=
          static_cast<std::int32_t>(language[input_channel]) *
          static_cast<std::int32_t>(read_i8(packed, language_weight + input_channel * kHidden + output_channel));
      language_gate[output_channel] +=
          static_cast<std::int32_t>(language[input_channel]) *
          static_cast<std::int32_t>(read_i8(packed, gate_weight + input_channel * kHidden + output_channel));
    }
  }

  for (int token = 0; token < kTokens; ++token) {
    for (int output_channel = 0; output_channel < kHidden; ++output_channel) {
      std::int32_t visual_candidate = 0;
      std::int32_t visual_gate = 0;
      for (int input_channel = 0; input_channel < kHidden; ++input_channel) {
#ifdef __SYNTHESIS__
#pragma HLS PIPELINE II = 1
#endif
        visual_candidate +=
            static_cast<std::int32_t>(input[token][input_channel]) *
            static_cast<std::int32_t>(read_i8(packed, visual_weight + input_channel * kHidden + output_channel));
        visual_gate +=
            static_cast<std::int32_t>(input[token][input_channel]) *
            static_cast<std::int32_t>(read_i8(packed, gate_weight + input_channel * kHidden + output_channel));
      }
      const float candidate = visual_candidate * input_scale * visual_weight_scale +
                              language_candidate[output_channel] * language_scale * language_weight_scale +
                              read_float(packed, bias + output_channel * sizeof(float));
      const float gate = sigmoid(visual_gate * input_scale * gate_weight_scale +
                                 language_gate[output_channel] * language_scale * gate_weight_scale);
      const float fused = (1.0f - gate) * static_cast<float>(input[token][output_channel]) * input_scale +
                          gate * std::tanh(candidate);
      output[token][output_channel] = quantize(fused, output_scale);
    }
  }
}

void decode_action(const ArenaWord* arena,
                   const ArenaWord* packed,
                   const std::int8_t fused[kTokens][kHidden],
                   float action[kActionValues]) {
  const float fusion_scale = read_float(packed, model::kFusion1Scale);
  const float state_scale = read_float(packed, model::kStateScale);
  const float hidden_scale = read_float(packed, model::kHiddenScale);
  const float state_input_scale = read_float(packed, model::kStateInputScale);
  const float state_weight_scale = read_float(packed, model::kStateWeightScale);
  const float action_input_weight_scale = read_float(packed, model::kActionInputWeightScale);
  const float action_output_weight_scale = read_float(packed, model::kActionOutputWeightScale);
  std::int8_t state_q[kState];
  std::int8_t pooled_q[kHidden];
  std::int8_t hidden_q[kActionHidden];

  for (int input_channel = 0; input_channel < kState; ++input_channel) {
    const float normalized =
        static_cast<float>(read_i16(arena, kStateOffset + input_channel * sizeof(std::int16_t))) *
        kStateNormalization;
    state_q[input_channel] = quantize(normalized, state_input_scale);
  }
  for (int output_channel = 0; output_channel < kHidden; ++output_channel) {
    std::int32_t fused_sum = 0;
    for (int token = 0; token < kTokens; ++token) {
      fused_sum += fused[token][output_channel];
    }
    std::int32_t state_accumulator = 0;
    for (int input_channel = 0; input_channel < kState; ++input_channel) {
      state_accumulator +=
          static_cast<std::int32_t>(state_q[input_channel]) *
          static_cast<std::int32_t>(read_i8(
              packed, model::kStateProjection + input_channel * kHidden + output_channel));
    }
    float value = static_cast<float>(fused_sum) * fusion_scale / static_cast<float>(kTokens) +
                  state_accumulator * state_input_scale * state_weight_scale +
                  read_float(packed, model::kStateBias + output_channel * sizeof(float));
    if (value < 0.0f) {
      value = 0.0f;
    }
    pooled_q[output_channel] = quantize(value, state_scale);
  }

  for (int output_channel = 0; output_channel < kActionHidden; ++output_channel) {
    std::int32_t accumulator = 0;
    for (int input_channel = 0; input_channel < kHidden; ++input_channel) {
      accumulator +=
          static_cast<std::int32_t>(pooled_q[input_channel]) *
          static_cast<std::int32_t>(read_i8(
              packed, model::kActionInput + input_channel * kActionHidden + output_channel));
    }
    float value = accumulator * state_scale * action_input_weight_scale +
                  read_float(packed, model::kActionInputBias + output_channel * sizeof(float));
    if (value < 0.0f) {
      value = 0.0f;
    }
    hidden_q[output_channel] = quantize(value, hidden_scale);
  }

  for (int output_channel = 0; output_channel < static_cast<int>(kActionValues); ++output_channel) {
    std::int32_t accumulator = 0;
    for (int input_channel = 0; input_channel < kActionHidden; ++input_channel) {
      accumulator +=
          static_cast<std::int32_t>(hidden_q[input_channel]) *
          static_cast<std::int32_t>(read_i8(
              packed, model::kActionOutput + input_channel * kActionValues + output_channel));
    }
    const float logit = accumulator * hidden_scale * action_output_weight_scale +
                        read_float(packed, model::kActionOutputBias + output_channel * sizeof(float));
    action[output_channel] = std::tanh(logit);
  }
}

}  // namespace

int run(ArenaWord* arena) {
  const ErrorCode validation = validate(arena);
  if (validation != ErrorCode::kNone) {
    finish(arena, validation);
    return static_cast<int>(validation);
  }

  const ArenaWord* packed = arena + kModelOffset / sizeof(ArenaWord);
  std::int8_t visual[kTokens][kHidden];
  std::int8_t language[kHidden];
  std::int8_t fusion_0[kTokens][kHidden];
  std::int8_t fusion_1[kTokens][kHidden];
  float action[kActionValues];
  encode_visual(arena, packed, visual);
  const std::uint16_t instruction = read_u16(arena, kHeaderInstructionId);
  for (int channel = 0; channel < kHidden; ++channel) {
    language[channel] = read_i8(packed, model::kInstructionTable + instruction * kHidden + channel);
  }
  fuse_layer(packed, 0, language, visual, fusion_0);
  fuse_layer(packed, 1, language, fusion_0, fusion_1);
  decode_action(arena, packed, fusion_1, action);
  for (std::size_t index = 0; index < kActionValues; ++index) {
    write_float(arena, kActionOffset + index * sizeof(float), action[index]);
  }
  finish(arena, ErrorCode::kNone);
  return 0;
}

}  // namespace e2e
}  // namespace hls
}  // namespace turbovla

int turbovla_lite_e2e(turbovla::hls::e2e::ArenaWord* arena) {
#ifdef __SYNTHESIS__
#pragma HLS INTERFACE m_axi port = arena offset = slave depth = 50080 bundle = gmem0
#pragma HLS INTERFACE s_axilite port = arena bundle = control
#pragma HLS INTERFACE s_axilite port = return bundle = control
#endif
  return turbovla::hls::e2e::run(arena);
}
