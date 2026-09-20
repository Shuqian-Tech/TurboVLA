#include "turbovla_runtime.hpp"

#include <iostream>

int main() {
  turbovla::runtime::RuntimeConfig config;
  auto pl_executor = [](const turbovla::runtime::FrameInput&, turbovla::runtime::ActionOutput& output,
                        std::uint32_t) {
    output.action.fill(0.25f);
    return true;
  };
  turbovla::runtime::TurboVlaRuntime runtime(config, pl_executor);
  turbovla::runtime::FrameInput input;
  turbovla::runtime::ActionOutput output;
  if (runtime.run(input, output) != turbovla::runtime::ErrorCode::kNone || output.action[0] != 0.25f) {
    return 1;
  }
  input.instruction_id = 255;
  if (runtime.run(input, output) != turbovla::runtime::ErrorCode::kNone) {
    return 2;
  }
  input.instruction_id = 256;
  if (runtime.run(input, output) != turbovla::runtime::ErrorCode::kInvalidInstructionId) {
    return 3;
  }
  runtime.set_hardware_contract_version(0x00020000);
  input.instruction_id = 0;
  if (runtime.run(input, output) != turbovla::runtime::ErrorCode::kContractMismatch) {
    return 4;
  }
  turbovla::runtime::TurboVlaRuntime timeout_runtime(config,
                                                      [](const auto&, auto&, std::uint32_t) { return false; });
  if (timeout_runtime.run(input, output) != turbovla::runtime::ErrorCode::kDmaTimeout) {
    return 5;
  }
  std::cout << "runtime register/DMA model passed\n";
  return 0;
}
