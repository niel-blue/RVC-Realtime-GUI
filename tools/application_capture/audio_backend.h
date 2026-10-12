#ifndef AUDIO_BRIDGE_AUDIO_BACKEND_H_
#define AUDIO_BRIDGE_AUDIO_BACKEND_H_

#include <functional>
#include <string>

namespace audio_bridge::audio {

enum class Status {
  kOff,
  kStarting,
  kActive,
  kUnavailable,
};

struct Config {
  std::string input_id;
  std::string output_id;
  bool exclusive = false;
  double host_sample_rate = 0.0;
};

using StatusCallback = std::function<void(Status, const std::string&)>;

}  // namespace audio_bridge::audio

#endif
