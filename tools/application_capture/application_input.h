// Copyright (c) 2026 niel

#ifndef AUDIO_BRIDGE_APPLICATION_INPUT_H_
#define AUDIO_BRIDGE_APPLICATION_INPUT_H_

#include <cstddef>
#include <cstdint>
#include <functional>
#include <memory>
#include <optional>
#include <string>
#include <string_view>
#include <vector>

#include "audio_backend.h"

namespace audio_bridge::audio {

// A Windows render-audio session that can be used as Audio-Bridge's input.
// The executable identity is suitable for VST state persistence; a process ID
// is intentionally runtime-only and must be resolved again after a restart.
struct ApplicationInputInfo {
  std::string identity;
  std::string display_name;
  std::uint32_t process_id = 0;
  bool active = false;
};

struct ApplicationInputSnapshot {
  std::vector<ApplicationInputInfo> applications;
  std::string error;
};

struct ApplicationInputExclusions {
  std::vector<std::uint32_t> process_ids;
  std::vector<std::string> identities;
};

auto EnumerateApplicationInputs(
    const ApplicationInputExclusions& exclusions = {})
    -> ApplicationInputSnapshot;
auto CurrentApplicationInputIdentity() -> std::string;
auto CurrentApplicationInputProcessId() -> std::uint32_t;
auto CurrentApplicationInputExclusions() -> ApplicationInputExclusions;
auto MergeRememberedApplicationInput(
    ApplicationInputSnapshot snapshot, std::string_view identity,
    const ApplicationInputExclusions& exclusions = {})
    -> ApplicationInputSnapshot;
auto FindApplicationInput(const ApplicationInputSnapshot& snapshot,
                          const std::string& identity)
    -> std::optional<ApplicationInputInfo>;

// Captures only the selected application's process tree through Windows
// process-loopback. Read() is non-blocking and zero-fills unavailable frames.
class ApplicationInput final {
 public:
  using StatusCallback =
      std::function<void(Status status, const std::string& error)>;

  explicit ApplicationInput(StatusCallback callback = {});
  ~ApplicationInput();

  ApplicationInput(const ApplicationInput&) = delete;
  auto operator=(const ApplicationInput&) -> ApplicationInput& = delete;

  auto Start(std::uint32_t process_id, double output_sample_rate) -> bool;
  void Stop();
  auto Read(float* left, float* right, std::size_t count) noexcept
      -> std::size_t;
  [[nodiscard]] auto GetStatus() const noexcept -> Status;
  [[nodiscard]] auto GetLastError() const -> std::string;

 private:
  class Impl;
  std::unique_ptr<Impl> impl_;
};

}  // namespace audio_bridge::audio

#endif
