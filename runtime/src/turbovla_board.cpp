#include "turbovla_runtime.hpp"

#include <xrt/xrt_bo.h>
#include <xrt/xrt_device.h>

#include <algorithm>
#include <array>
#include <chrono>
#include <cmath>
#include <cstddef>
#include <cstdint>
#include <cstring>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <limits>
#include <stdexcept>
#include <string>
#include <vector>

#include <fcntl.h>
#include <sys/mman.h>
#include <unistd.h>

namespace {

namespace fs = std::filesystem;
using turbovla::runtime::ActionOutput;
using turbovla::runtime::ArenaBuffer;
using turbovla::runtime::CacheMaintenance;
using turbovla::runtime::ErrorCode;
using turbovla::runtime::FrameInput;
using turbovla::runtime::PlArenaExecutor;
using turbovla::runtime::VolatileRegisterIo;
using turbovla::runtime::kActionValues;
using turbovla::runtime::kArenaBytes;
using turbovla::runtime::kControlOffset;
using turbovla::runtime::kGlobalInterruptOffset;
using turbovla::runtime::kImageBytes;
using turbovla::runtime::kInterruptEnableOffset;
using turbovla::runtime::kInterruptStatusOffset;
using turbovla::runtime::kModelBytes;
using turbovla::runtime::kStateValues;

constexpr std::uint32_t kBoardTimeoutPolls = 200000000U;

std::vector<std::uint8_t> read_file(const fs::path& path, std::size_t expected_bytes) {
  std::ifstream stream(path, std::ios::binary | std::ios::ate);
  if (!stream) {
    throw std::runtime_error("cannot open " + path.string());
  }
  const auto size = stream.tellg();
  if (size < 0 || static_cast<std::size_t>(size) != expected_bytes) {
    throw std::runtime_error("unexpected size for " + path.string());
  }
  std::vector<std::uint8_t> data(expected_bytes);
  stream.seekg(0);
  stream.read(reinterpret_cast<char*>(data.data()), size);
  if (!stream) {
    throw std::runtime_error("cannot read " + path.string());
  }
  return data;
}

std::string read_text(const fs::path& path) {
  std::ifstream stream(path);
  std::string text;
  std::getline(stream, text);
  if (!stream) {
    throw std::runtime_error("cannot read " + path.string());
  }
  return text;
}

fs::path find_uio(const std::string& expected_name) {
  for (const auto& entry : fs::directory_iterator("/sys/class/uio")) {
    if (read_text(entry.path() / "name") == expected_name) {
      return fs::path("/dev") / entry.path().filename();
    }
  }
  throw std::runtime_error("UIO device not found: " + expected_name);
}

std::size_t uio_map_size(const fs::path& device) {
  const fs::path size_path = fs::path("/sys/class/uio") / device.filename() / "maps/map0/size";
  return static_cast<std::size_t>(std::stoull(read_text(size_path), nullptr, 0));
}

class UioRegisters {
 public:
  explicit UioRegisters(const std::string& name) {
    const auto device = find_uio(name);
    bytes_ = uio_map_size(device);
    fd_ = open(device.c_str(), O_RDWR | O_CLOEXEC);
    if (fd_ < 0) {
      throw std::runtime_error("cannot open " + device.string());
    }
    mapping_ = mmap(nullptr, bytes_, PROT_READ | PROT_WRITE, MAP_SHARED, fd_, 0);
    if (mapping_ == MAP_FAILED) {
      close(fd_);
      fd_ = -1;
      throw std::runtime_error("cannot mmap " + device.string());
    }
  }

  UioRegisters(const UioRegisters&) = delete;
  UioRegisters& operator=(const UioRegisters&) = delete;

  ~UioRegisters() {
    if (mapping_ != MAP_FAILED) {
      munmap(mapping_, bytes_);
    }
    if (fd_ >= 0) {
      close(fd_);
    }
  }

  volatile std::uint32_t* data() const {
    return static_cast<volatile std::uint32_t*>(mapping_);
  }
  std::size_t words() const { return bytes_ / sizeof(std::uint32_t); }

 private:
  int fd_ = -1;
  void* mapping_ = MAP_FAILED;
  std::size_t bytes_ = 0;
};

class XrtArena final : public CacheMaintenance {
 public:
  XrtArena() {
    device_ = xrtDeviceOpen(0);
    if (device_ == nullptr) {
      throw std::runtime_error("cannot open XRT device 0; verify the xlnx,zocl overlay node");
    }
    buffer_ = xrtBOAlloc(device_, kArenaBytes, 0, 0);
    if (buffer_ == nullptr) {
      xrtDeviceClose(device_);
      device_ = nullptr;
      throw std::runtime_error("cannot allocate XRT arena buffer");
    }
    data_ = static_cast<std::uint8_t*>(xrtBOMap(buffer_));
    address_ = xrtBOAddress(buffer_);
    if (data_ == nullptr || address_ == std::numeric_limits<std::uint64_t>::max() || address_ == 0) {
      xrtBOFree(buffer_);
      xrtDeviceClose(device_);
      buffer_ = nullptr;
      device_ = nullptr;
      throw std::runtime_error("XRT arena has no usable mapping or device address");
    }
    std::memset(data_, 0, kArenaBytes);
  }

  XrtArena(const XrtArena&) = delete;
  XrtArena& operator=(const XrtArena&) = delete;

  ~XrtArena() override {
    if (buffer_ != nullptr) {
      xrtBOFree(buffer_);
    }
    if (device_ != nullptr) {
      xrtDeviceClose(device_);
    }
  }

  ArenaBuffer arena() const { return {data_, address_, kArenaBytes}; }

  void flush(std::size_t offset, std::size_t bytes) override {
    if (xrtBOSync(buffer_, XCL_BO_SYNC_BO_TO_DEVICE, bytes, offset) != 0) {
      throw std::runtime_error("XRT host-to-device sync failed");
    }
  }

  void invalidate(std::size_t offset, std::size_t bytes) override {
    if (xrtBOSync(buffer_, XCL_BO_SYNC_BO_FROM_DEVICE, bytes, offset) != 0) {
      throw std::runtime_error("XRT device-to-host sync failed");
    }
  }

 private:
  xrtDeviceHandle device_ = nullptr;
  xrtBufferHandle buffer_ = nullptr;
  std::uint8_t* data_ = nullptr;
  std::uint64_t address_ = 0;
};

int run(const fs::path& fixture, const std::string& uio_name, bool probe_only) {
  const auto model = read_file(fixture / "model.bin", kModelBytes);
  const auto image = read_file(fixture / "image.bin", kImageBytes);
  const auto state = read_file(fixture / "state.bin", kStateValues * sizeof(std::int16_t));
  const auto instruction = read_file(fixture / "instruction_id.bin", sizeof(std::uint16_t));
  const auto expected_bytes = read_file(fixture / "action.bin", kActionValues * sizeof(float));

  std::cout << "KR260 board stage=open_uio name=" << uio_name << std::endl;
  UioRegisters mapped_registers(uio_name);
  VolatileRegisterIo registers(mapped_registers.data(), mapped_registers.words());
  std::cout << "KR260 board stage=uio_ready control=0x" << std::hex
            << registers.read32(kControlOffset) << std::dec << std::endl;

  std::cout << "KR260 board stage=open_xrt" << std::endl;
  XrtArena arena;
  const auto arena_buffer = arena.arena();
  std::cout << "KR260 board stage=xrt_ready arena_address=0x" << std::hex
            << arena_buffer.physical_address << std::dec << " arena_bytes=" << arena_buffer.bytes
            << std::endl;
  PlArenaExecutor executor(arena.arena(), registers, arena);
  if (executor.load_model(model.data(), model.size()) != ErrorCode::kNone) {
    throw std::runtime_error("model contract rejected before board execution");
  }
  std::cout << "KR260 board stage=model_ready" << std::endl;

  if (probe_only) {
    std::cout << "KR260 board probe passed; PL start not issued" << std::endl;
    return 0;
  }

  FrameInput input;
  std::copy(image.begin(), image.end(), input.image.begin());
  std::memcpy(input.state.data(), state.data(), state.size());
  input.instruction_id = static_cast<std::uint16_t>(instruction[0]) |
                         (static_cast<std::uint16_t>(instruction[1]) << 8U);

  ActionOutput output;
  std::cout << "KR260 board stage=start_pl" << std::endl;
  const auto start_time = std::chrono::steady_clock::now();
  const auto result = executor.run(input, output, kBoardTimeoutPolls);
  const auto end_time = std::chrono::steady_clock::now();
  const auto elapsed_us = std::chrono::duration_cast<std::chrono::microseconds>(end_time - start_time).count();
  std::cout << "KR260 board pl_elapsed_us=" << elapsed_us << std::endl;
  std::cout << "KR260 board stage=pl_return result=" << static_cast<std::uint32_t>(result)
            << std::endl;
  std::cout << "KR260 board interrupts gie=0x" << std::hex
            << registers.read32(kGlobalInterruptOffset) << " ier=0x"
            << registers.read32(kInterruptEnableOffset) << " isr=0x"
            << registers.read32(kInterruptStatusOffset) << std::dec << std::endl;
  if (result != ErrorCode::kNone) {
    throw std::runtime_error("PL inference failed with error " +
                             std::to_string(static_cast<std::uint32_t>(result)));
  }

  std::array<float, kActionValues> expected{};
  std::memcpy(expected.data(), expected_bytes.data(), expected_bytes.size());
  float max_error = 0.0F;
  float total_error = 0.0F;
  for (std::size_t index = 0; index < kActionValues; ++index) {
    if (!std::isfinite(output.action[index]) || !std::isfinite(expected[index])) {
      throw std::runtime_error("non-finite action at index " + std::to_string(index));
    }
    const float error = std::abs(output.action[index] - expected[index]);
    max_error = std::max(max_error, error);
    total_error += error;
  }
  const float mean_error = total_error / static_cast<float>(kActionValues);
  std::cout << "KR260 action parity max_abs_error=" << max_error
            << " mean_abs_error=" << mean_error << '\n';
  return max_error <= 1.0e-5F && mean_error <= 1.0e-6F ? 0 : 1;
}

}  // namespace

int main(int argc, char** argv) {
  if (argc < 2 || argc > 4) {
    std::cerr << "usage: turbovla_board <fixture-dir> [uio-name] [--probe-only]\n";
    return 2;
  }
  std::string uio_name = "turbovla-lite-e2e";
  bool uio_name_set = false;
  bool probe_only = false;
  for (int index = 2; index < argc; ++index) {
    const std::string argument = argv[index];
    if (argument == "--probe-only") {
      probe_only = true;
    } else if (!uio_name_set) {
      uio_name = argument;
      uio_name_set = true;
    } else {
      std::cerr << "usage: turbovla_board <fixture-dir> [uio-name] [--probe-only]\n";
      return 2;
    }
  }
  try {
    return run(argv[1], uio_name, probe_only);
  } catch (const std::exception& error) {
    std::cerr << "turbovla_board: " << error.what() << '\n';
    return 3;
  }
}
