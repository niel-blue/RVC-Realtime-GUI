// Copyright (c) 2026 niel

#include "application_input.h"

#include <algorithm>
#include <array>
#include <atomic>
#include <cctype>
#include <chrono>
#include <cmath>
#include <condition_variable>
#include <cstdio>
#include <cstring>
#include <filesystem>
#include <future>
#include <map>
#include <mutex>
#include <ranges>
#include <thread>
#include <utility>
#include <vector>

#ifdef _WIN32

#define NOMINMAX
#define WIN32_LEAN_AND_MEAN
#include <Windows.h>

#include <Audioclient.h>
#include <audioclientactivationparams.h>
#include <audiopolicy.h>
#include <ksmedia.h>
#include <mmdeviceapi.h>
#include <wrl/client.h>
#include <wrl/implements.h>

#endif

namespace audio_bridge::audio {
namespace {

auto LowerAscii(std::string value) -> std::string {
  std::ranges::transform(value, value.begin(), [](const unsigned char value) {
    return static_cast<char>(std::tolower(value));
  });
  return value;
}

auto IsExcluded(const ApplicationInputExclusions& exclusions,
                const std::uint32_t process_id,
                const std::string_view identity) -> bool {
  if (std::ranges::find(exclusions.process_ids, process_id) !=
      exclusions.process_ids.end()) {
    return true;
  }
  const auto normalized = LowerAscii(std::string(identity));
  return std::ranges::any_of(exclusions.identities,
                             [&normalized](const std::string& value) {
    return !normalized.empty() && normalized == LowerAscii(value);
  });
}

// A bounded SPSC queue dedicated to the process-loopback worker. It avoids
// sharing the endpoint FIFOs because its producer runs at a different clock.
class ProcessFifo final {
 public:
  explicit ProcessFifo(const std::size_t capacity)
      : frames_(std::max<std::size_t>(capacity, 1)) {}

  void Push(const float* const left, const float* const right,
            const std::size_t count) noexcept {
    if (left == nullptr || count == 0) {
      return;
    }
    const auto write = write_.load(std::memory_order_relaxed);
    const auto read = read_.load(std::memory_order_acquire);
    const auto used = write > read ? std::min(write - read, frames_.size()) : 0;
    if (count > frames_.size() - used) {
      overflows_.fetch_add(count, std::memory_order_relaxed);
      return;
    }
    for (auto index = std::size_t{0}; index < count; ++index) {
      frames_[(write + index) % frames_.size()] = {
          left[index], right == nullptr ? left[index] : right[index]};
    }
    write_.store(write + count, std::memory_order_release);
  }

  auto Pop(float& left, float& right) noexcept -> bool {
    const auto read = read_.load(std::memory_order_relaxed);
    const auto write = write_.load(std::memory_order_acquire);
    if (read == write) {
      left = 0.0F;
      right = 0.0F;
      underruns_.fetch_add(1, std::memory_order_relaxed);
      return false;
    }
    const auto& frame = frames_[read % frames_.size()];
    left = frame[0];
    right = frame[1];
    read_.store(read + 1, std::memory_order_release);
    return true;
  }

  [[nodiscard]] auto Size() const noexcept -> std::size_t {
    const auto write = write_.load(std::memory_order_acquire);
    const auto read = read_.load(std::memory_order_acquire);
    return write > read ? std::min(write - read, frames_.size()) : 0;
  }
  [[nodiscard]] auto UnderrunCount() const noexcept -> std::uint64_t {
    return underruns_.load(std::memory_order_relaxed);
  }
  [[nodiscard]] auto OverflowCount() const noexcept -> std::uint64_t {
    return overflows_.load(std::memory_order_relaxed);
  }
  void ResetStats() noexcept {
    underruns_.store(0, std::memory_order_relaxed);
    overflows_.store(0, std::memory_order_relaxed);
  }
  void Clear() noexcept {
    read_.store(write_.load(std::memory_order_acquire),
                std::memory_order_release);
  }

 private:
  std::vector<std::array<float, 2>> frames_;
  std::atomic<std::size_t> read_ = 0;
  std::atomic<std::size_t> write_ = 0;
  std::atomic<std::uint64_t> underruns_ = 0;
  std::atomic<std::uint64_t> overflows_ = 0;
};

#ifdef _WIN32

using Microsoft::WRL::ComPtr;

auto WideToUtf8(const std::wstring& text) -> std::string {
  if (text.empty()) {
    return {};
  }
  const auto size = WideCharToMultiByte(CP_UTF8, WC_ERR_INVALID_CHARS,
                                        text.data(),
                                        static_cast<int>(text.size()), nullptr,
                                        0, nullptr, nullptr);
  if (size <= 0) {
    return {};
  }
  auto result = std::string(static_cast<std::size_t>(size), '\0');
  WideCharToMultiByte(CP_UTF8, WC_ERR_INVALID_CHARS, text.data(),
                      static_cast<int>(text.size()), result.data(), size,
                      nullptr, nullptr);
  return result;
}

auto HResultText(const char* const operation, const HRESULT result)
    -> std::string {
  char value[16]{};
  std::snprintf(value, sizeof(value), "%08lX",
                static_cast<unsigned long>(result));
  return std::string(operation) + " failed (0x" + value + ").";
}

auto ProcessImagePath(const DWORD process_id) -> std::wstring {
  const auto process = OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, FALSE,
                                   process_id);
  if (process == nullptr) {
    return {};
  }
  auto path = std::wstring(32768, L'\0');
  auto size = static_cast<DWORD>(path.size());
  const auto success =
      QueryFullProcessImageNameW(process, 0, path.data(), &size) != FALSE;
  CloseHandle(process);
  if (!success) {
    return {};
  }
  path.resize(size);
  return path;
}

auto DisplayName(const std::wstring& path, const std::string& fallback)
    -> std::string {
  if (!path.empty()) {
    const auto filename = std::filesystem::path(path).filename().wstring();
    const auto utf8 = WideToUtf8(filename);
    if (!utf8.empty()) {
      return utf8;
    }
  }
  return fallback.empty() ? "Unknown application" : fallback;
}

#endif

}  // namespace

auto CurrentApplicationInputIdentity() -> std::string {
#ifdef _WIN32
  return LowerAscii(WideToUtf8(ProcessImagePath(GetCurrentProcessId())));
#else
  return {};
#endif
}

auto CurrentApplicationInputProcessId() -> std::uint32_t {
#ifdef _WIN32
  return static_cast<std::uint32_t>(GetCurrentProcessId());
#else
  return 0;
#endif
}

auto CurrentApplicationInputExclusions() -> ApplicationInputExclusions {
  auto exclusions = ApplicationInputExclusions{};
  if (const auto process_id = CurrentApplicationInputProcessId();
      process_id != 0) {
    exclusions.process_ids.push_back(process_id);
  }
  if (const auto identity = CurrentApplicationInputIdentity();
      !identity.empty()) {
    exclusions.identities.push_back(identity);
  }
  return exclusions;
}

auto EnumerateApplicationInputs(const ApplicationInputExclusions& exclusions)
    -> ApplicationInputSnapshot {
#ifdef _WIN32
  const auto com_result = CoInitializeEx(nullptr, COINIT_MULTITHREADED);
  if (FAILED(com_result) && com_result != RPC_E_CHANGED_MODE) {
    return {.error = HResultText("Initializing Application Input", com_result)};
  }
  const auto uninitialize = SUCCEEDED(com_result);
  auto finish = [&]() {
    if (uninitialize) {
      CoUninitialize();
    }
  };

  auto result = ApplicationInputSnapshot{};
  ComPtr<IMMDeviceEnumerator> enumerator;
  const auto create = CoCreateInstance(__uuidof(MMDeviceEnumerator), nullptr,
                                       CLSCTX_ALL, IID_PPV_ARGS(&enumerator));
  if (FAILED(create)) {
    result.error = HResultText("Creating the audio device registry", create);
    finish();
    return result;
  }
  ComPtr<IMMDeviceCollection> devices;
  const auto enumerate =
      enumerator->EnumAudioEndpoints(eRender, DEVICE_STATE_ACTIVE, &devices);
  if (FAILED(enumerate)) {
    result.error = HResultText("Enumerating audio output devices", enumerate);
    finish();
    return result;
  }

  std::map<DWORD, ApplicationInputInfo> processes;
  UINT device_count = 0;
  static_cast<void>(devices->GetCount(&device_count));
  for (UINT device_index = 0; device_index < device_count; ++device_index) {
    ComPtr<IMMDevice> device;
    if (FAILED(devices->Item(device_index, &device))) {
      continue;
    }
    ComPtr<IAudioSessionManager2> manager;
    if (FAILED(device->Activate(__uuidof(IAudioSessionManager2), CLSCTX_ALL,
                               nullptr, reinterpret_cast<void**>(
                                            manager.GetAddressOf())))) {
      continue;
    }
    ComPtr<IAudioSessionEnumerator> sessions;
    if (FAILED(manager->GetSessionEnumerator(&sessions))) {
      continue;
    }
    int session_count = 0;
    if (FAILED(sessions->GetCount(&session_count))) {
      continue;
    }
    for (int session_index = 0; session_index < session_count;
         ++session_index) {
      ComPtr<IAudioSessionControl> control;
      if (FAILED(sessions->GetSession(session_index, &control))) {
        continue;
      }
      AudioSessionState state = AudioSessionStateInactive;
      if (FAILED(control->GetState(&state)) ||
          state == AudioSessionStateExpired) {
        continue;
      }
      ComPtr<IAudioSessionControl2> control2;
      DWORD process_id = 0;
      if (FAILED(control.As(&control2)) ||
          FAILED(control2->GetProcessId(&process_id)) || process_id == 0) {
        continue;
      }
      LPWSTR session_name = nullptr;
      auto fallback = std::string{};
      if (SUCCEEDED(control->GetDisplayName(&session_name)) &&
          session_name != nullptr) {
        fallback = WideToUtf8(session_name);
        CoTaskMemFree(session_name);
      }
      const auto image_path = ProcessImagePath(process_id);
      const auto display = DisplayName(image_path, fallback);
      auto identity = LowerAscii(WideToUtf8(image_path));
      if (identity.empty()) {
        identity = LowerAscii(display);
      }
      if (IsExcluded(exclusions, process_id, identity)) {
        continue;
      }
      const auto active = state == AudioSessionStateActive;
      auto [entry, inserted] = processes.emplace(
          process_id, ApplicationInputInfo{identity, display, process_id,
                                            active});
      if (!inserted) {
        entry->second.active = entry->second.active || active;
        if (entry->second.display_name == "Unknown application" &&
            display != "Unknown application") {
          entry->second.display_name = display;
          entry->second.identity = identity;
        }
      }
    }
  }
  finish();
  for (auto& [process_id, application] : processes) {
    static_cast<void>(process_id);
    result.applications.push_back(std::move(application));
  }
  std::ranges::sort(result.applications,
                    [](const auto& left, const auto& right) {
    return LowerAscii(left.display_name) < LowerAscii(right.display_name);
  });
  return result;
#else
  static_cast<void>(exclusions);
  return {.error = "Application Input is available on Windows only."};
#endif
}

auto MergeRememberedApplicationInput(
    ApplicationInputSnapshot snapshot, const std::string_view identity,
    const ApplicationInputExclusions& exclusions) -> ApplicationInputSnapshot {
  if (identity.empty()) {
    return snapshot;
  }
  const auto normalized = LowerAscii(std::string(identity));
  if (IsExcluded(exclusions, 0, normalized) ||
      std::ranges::any_of(snapshot.applications,
                          [&normalized](const auto& application) {
    return LowerAscii(application.identity) == normalized;
  })) {
    return snapshot;
  }
  auto display = normalized;
  if (const auto separator = display.find_last_of("\\\\/");
      separator != std::string::npos && separator + 1U < display.size()) {
    display.erase(0, separator + 1U);
  }
  snapshot.applications.push_back(
      {.identity = normalized, .display_name = std::move(display)});
  std::ranges::sort(snapshot.applications,
                    [](const auto& left, const auto& right) {
    return LowerAscii(left.display_name) < LowerAscii(right.display_name);
  });
  return snapshot;
}

auto FindApplicationInput(const ApplicationInputSnapshot& snapshot,
                          const std::string& identity)
    -> std::optional<ApplicationInputInfo> {
  const auto normalized = LowerAscii(identity);
  if (normalized.empty()) {
    return std::nullopt;
  }
  for (const auto& application : snapshot.applications) {
    if (LowerAscii(application.identity) == normalized) {
      return application;
    }
  }
  return std::nullopt;
}

class ApplicationInput::Impl final {
 public:
  explicit Impl(StatusCallback callback) : callback_(std::move(callback)) {}
  ~Impl() { Stop(); }

  auto Start(const std::uint32_t process_id, const double output_sample_rate)
      -> bool {
    Stop();
    if (process_id == 0 || !std::isfinite(output_sample_rate) ||
        output_sample_rate <= 0.0) {
      SetStatus(Status::kUnavailable, "Select an active audio application.");
      return false;
    }
#ifdef _WIN32
    target_rate_ = output_sample_rate;
    source_rate_ = 44100.0;
    nominal_ratio_ = 1.0;
    ratio_ = 1.0;
    target_frames_ = 0;
    control_frames_ = 0;
    smoothed_frames_ = 0.0;
    integral_ = 0.0;
    position_ = 0.0;
    resampler_ready_ = false;
    control_initialized_ = false;
    recovery_pending_ = false;
    playback_started_ = false;
    recovery_armed_ = false;
    handled_underruns_ = 0;
    handled_overflows_ = 0;
    handled_discontinuities_ = 0;
    discontinuities_.store(0, std::memory_order_release);
    fifo_.ResetStats();
    fifo_.Clear();
    stop_event_ = CreateEventW(nullptr, TRUE, FALSE, nullptr);
    if (stop_event_ == nullptr) {
      SetStatus(Status::kUnavailable,
                "The Application Input stop event could not be created.");
      return false;
    }
    SetStatus(Status::kStarting, {});
    auto promise = std::promise<bool>{};
    auto ready = promise.get_future();
    worker_ = std::thread(&Impl::Run, this, process_id, std::move(promise));
    if (!ready.get()) {
      if (worker_.joinable()) {
        worker_.join();
      }
      CloseHandle(stop_event_);
      stop_event_ = nullptr;
      return false;
    }
    return true;
#else
    static_cast<void>(output_sample_rate);
    SetStatus(Status::kUnavailable, "Application Input is available on Windows only.");
    return false;
#endif
  }

  void Stop() {
#ifdef _WIN32
    if (stop_event_ != nullptr) {
      SetEvent(stop_event_);
    }
    if (worker_.joinable()) {
      worker_.join();
    }
    if (stop_event_ != nullptr) {
      CloseHandle(stop_event_);
      stop_event_ = nullptr;
    }
#endif
    fifo_.Clear();
    resampler_ready_ = false;
    recovery_pending_ = false;
    control_initialized_ = false;
    control_frames_ = 0;
    smoothed_frames_ = 0.0;
    integral_ = 0.0;
    nominal_ratio_ = 1.0;
    ratio_ = 1.0;
    target_frames_ = 0;
    playback_started_ = false;
    recovery_armed_ = false;
    handled_underruns_ = 0;
    handled_overflows_ = 0;
    handled_discontinuities_ = 0;
    discontinuities_.store(0, std::memory_order_release);
    SetStatus(Status::kOff, {});
  }

  auto Read(float* const left, float* const right, const std::size_t count)
      noexcept -> std::size_t {
    if (left == nullptr || count == 0) {
      return 0;
    }
    const auto active = GetStatus() == Status::kActive;
    if (active && recovery_pending_) {
      if (fifo_.Size() >= target_frames_) {
        recovery_pending_ = false;
        resampler_ready_ = false;
        position_ = 0.0;
        integral_ = 0.0;
        ratio_ = nominal_ratio_;
        smoothed_frames_ = static_cast<double>(fifo_.Size());
        control_frames_ = 0;
      } else {
        std::fill_n(left, count, 0.0F);
        if (right != nullptr) {
          std::fill_n(right, count, 0.0F);
        }
        return 0;
      }
    }
    auto received = std::size_t{0};
    for (auto index = std::size_t{0}; index < count; ++index) {
      auto sample_left = 0.0F;
      auto sample_right = 0.0F;
      if (active && ReadResampled(sample_left, sample_right)) {
        ++received;
      }
      left[index] = sample_left;
      if (right != nullptr) {
        right[index] = sample_right;
      }
    }
    if (received != 0) {
      playback_started_ = true;
    }
    if (active) {
      UpdateClockControl(count);
      const auto underruns = fifo_.UnderrunCount();
      const auto overflows = fifo_.OverflowCount();
      const auto discontinuities =
          discontinuities_.load(std::memory_order_acquire);
      // Initial empty reads are expected while the process-loopback stream
      // opens. Arm recovery only after the target fill is reached.
      if (!recovery_armed_ && target_frames_ != 0 &&
          fifo_.Size() >= target_frames_) {
        recovery_armed_ = true;
        handled_underruns_ = underruns;
        handled_overflows_ = overflows;
        handled_discontinuities_ = discontinuities;
      }
      if (playback_started_ && recovery_armed_ &&
          (underruns != handled_underruns_ ||
           overflows != handled_overflows_ ||
           discontinuities != handled_discontinuities_)) {
        BeginRecovery(overflows != handled_overflows_ ||
                      discontinuities != handled_discontinuities_);
        handled_underruns_ = underruns;
        handled_overflows_ = overflows;
        handled_discontinuities_ = discontinuities;
      }
    }
    return received;
  }

  [[nodiscard]] auto GetStatus() const noexcept -> Status {
    return status_.load(std::memory_order_acquire);
  }
  [[nodiscard]] auto GetLastError() const -> std::string {
    const auto lock = std::lock_guard(error_mutex_);
    return error_;
  }

 private:
  void SetStatus(const Status status, std::string error) {
    {
      const auto lock = std::lock_guard(error_mutex_);
      error_ = std::move(error);
    }
    status_.store(status, std::memory_order_release);
    if (callback_) {
      callback_(status, GetLastError());
    }
  }

  void BeginRecovery(const bool discard_fifo) noexcept {
    if (discard_fifo) {
      fifo_.Clear();
    }
    resampler_ready_ = false;
    position_ = 0.0;
    integral_ = 0.0;
    ratio_ = nominal_ratio_;
    smoothed_frames_ = static_cast<double>(fifo_.Size());
    control_frames_ = 0;
    recovery_pending_ = true;
  }

  auto ReadResampled(float& left, float& right) noexcept -> bool {
    if (!resampler_ready_) {
      if (!fifo_.Pop(current_left_, current_right_)) {
        return false;
      }
      if (!fifo_.Pop(next_left_, next_right_)) {
        next_left_ = current_left_;
        next_right_ = current_right_;
      }
      position_ = 0.0;
      resampler_ready_ = true;
    }
    left = static_cast<float>(current_left_ + position_ *
                              (next_left_ - current_left_));
    right = static_cast<float>(current_right_ + position_ *
                               (next_right_ - current_right_));
    position_ += ratio_;
    while (position_ >= 1.0) {
      current_left_ = next_left_;
      current_right_ = next_right_;
      if (!fifo_.Pop(next_left_, next_right_)) {
        next_left_ = current_left_;
        next_right_ = current_right_;
      }
      position_ -= 1.0;
    }
    return true;
  }

  void UpdateClockControl(const std::size_t output_frames) noexcept {
    if (!control_initialized_) {
      smoothed_frames_ = static_cast<double>(fifo_.Size());
      control_initialized_ = true;
    }
    if (target_rate_ <= 0.0 || source_rate_ <= 0.0 || target_frames_ == 0) {
      return;
    }
    control_frames_ += output_frames;
    const auto interval = static_cast<std::size_t>(std::max(
        1.0, std::round(target_rate_ * kClockControlIntervalSeconds)));
    if (control_frames_ < interval) {
      return;
    }
    const auto elapsed_seconds =
        static_cast<double>(control_frames_) / target_rate_;
    control_frames_ = 0;
    const auto occupancy = static_cast<double>(fifo_.Size());
    const auto smoothing = elapsed_seconds /
                           (kFifoSmoothingTimeSeconds + elapsed_seconds);
    smoothed_frames_ += std::clamp(smoothing, 0.01, 1.0) *
                        (occupancy - smoothed_frames_);
    const auto error_seconds =
        (smoothed_frames_ - static_cast<double>(target_frames_)) /
        source_rate_;
    const auto proportional = kClockProportionalGain * error_seconds;
    const auto integral_step =
        kClockIntegralGain * error_seconds * elapsed_seconds;
    const auto candidate_integral = std::clamp(
        integral_ + integral_step, -kMaxIntegralCorrection,
        kMaxIntegralCorrection);
    const auto candidate_correction = proportional + candidate_integral;
    const auto saturated_high = candidate_correction > kMaxCorrection &&
                                error_seconds > 0.0;
    const auto saturated_low = candidate_correction < -kMaxCorrection &&
                               error_seconds < 0.0;
    if (!saturated_high && !saturated_low) {
      integral_ = candidate_integral;
    }
    const auto correction = std::clamp(
        proportional + integral_, -kMaxCorrection, kMaxCorrection);
    ratio_ = nominal_ratio_ * (1.0 + correction);
  }

#ifdef _WIN32
  struct ActivationState {
    std::mutex mutex;
    std::condition_variable condition;
    HRESULT result = E_FAIL;
    ComPtr<IAudioClient> client;
    bool complete = false;
  };

  struct ActivationHandler final
      : public Microsoft::WRL::RuntimeClass<
            Microsoft::WRL::RuntimeClassFlags<Microsoft::WRL::ClassicCom>,
            Microsoft::WRL::FtmBase,
            IActivateAudioInterfaceCompletionHandler> {
   public:
    explicit ActivationHandler(std::shared_ptr<ActivationState> state)
        : state_(std::move(state)) {}

    auto STDMETHODCALLTYPE ActivateCompleted(
        IActivateAudioInterfaceAsyncOperation* const operation) -> HRESULT
        override {
      auto result = E_FAIL;
      auto activation_result = E_FAIL;
      ComPtr<IUnknown> activated;
      if (operation != nullptr) {
        result = operation->GetActivateResult(&activation_result, &activated);
        if (SUCCEEDED(result)) {
          result = activation_result;
        }
      }
      ComPtr<IAudioClient> client;
      if (SUCCEEDED(result) && activated != nullptr) {
        result = activated.As(&client);
      }
      {
        const auto lock = std::lock_guard(state_->mutex);
        state_->result = result;
        state_->client = std::move(client);
        state_->complete = true;
      }
      state_->condition.notify_one();
      return S_OK;
    }

   private:
    std::shared_ptr<ActivationState> state_;
  };

  static auto ReadSample(const BYTE* const data, const UINT32 frame,
                         const UINT32 channel,
                         const WAVEFORMATEX& format) noexcept -> float {
    if (data == nullptr || channel >= format.nChannels ||
        format.nBlockAlign == 0) {
      return 0.0F;
    }
    const auto bytes = static_cast<std::size_t>(format.wBitsPerSample / 8U);
    const auto* const sample = data + static_cast<std::size_t>(frame) *
                                   format.nBlockAlign + channel * bytes;
    if (format.wBitsPerSample == 16) {
      std::int16_t value = 0;
      std::memcpy(&value, sample, sizeof(value));
      return static_cast<float>(value) / 32768.0F;
    }
    if (format.wBitsPerSample == 32 &&
        format.wFormatTag == WAVE_FORMAT_IEEE_FLOAT) {
      float value = 0.0F;
      std::memcpy(&value, sample, sizeof(value));
      return value;
    }
    return 0.0F;
  }

  void Run(const std::uint32_t process_id, std::promise<bool> started) {
    const auto com_result = CoInitializeEx(nullptr, COINIT_MULTITHREADED);
    if (FAILED(com_result)) {
      SetStatus(Status::kUnavailable,
                HResultText("Initializing Application Input", com_result));
      started.set_value(false);
      return;
    }
    auto finish = []() { CoUninitialize(); };
    auto client = ComPtr<IAudioClient>{};
    auto capture = ComPtr<IAudioCaptureClient>{};
    auto audio_event = HANDLE{};
    const auto close_event = [&]() {
      if (audio_event != nullptr) {
        CloseHandle(audio_event);
        audio_event = nullptr;
      }
    };

    const auto activation = std::make_shared<ActivationState>();
    const auto handler = Microsoft::WRL::Make<ActivationHandler>(activation);
    if (handler == nullptr) {
      SetStatus(Status::kUnavailable,
                "The Application Input activation handler could not be created.");
      started.set_value(false);
      finish();
      return;
    }
    AUDIOCLIENT_ACTIVATION_PARAMS params{};
    params.ActivationType = AUDIOCLIENT_ACTIVATION_TYPE_PROCESS_LOOPBACK;
    params.ProcessLoopbackParams.ProcessLoopbackMode =
        PROCESS_LOOPBACK_MODE_INCLUDE_TARGET_PROCESS_TREE;
    params.ProcessLoopbackParams.TargetProcessId = process_id;
    PROPVARIANT activation_params{};
    activation_params.vt = VT_BLOB;
    activation_params.blob.cbSize = sizeof(params);
    activation_params.blob.pBlobData = reinterpret_cast<BYTE*>(&params);
    ComPtr<IActivateAudioInterfaceAsyncOperation> operation;
    auto result = ActivateAudioInterfaceAsync(
        VIRTUAL_AUDIO_DEVICE_PROCESS_LOOPBACK, __uuidof(IAudioClient),
        &activation_params, handler.Get(), &operation);
    if (FAILED(result)) {
      SetStatus(Status::kUnavailable,
                HResultText("Starting Application Input", result));
      started.set_value(false);
      finish();
      return;
    }
    {
      auto lock = std::unique_lock(activation->mutex);
      if (!activation->condition.wait_for(
              lock, std::chrono::seconds(5),
              [&]() { return activation->complete; }) ||
          FAILED(activation->result) || activation->client == nullptr) {
        const auto error = activation->complete
                               ? HResultText("Activating Application Input",
                                             activation->result)
                               : "Application Input activation timed out.";
        SetStatus(Status::kUnavailable, error);
        started.set_value(false);
        finish();
        return;
      }
      client = activation->client;
    }

    // The virtual endpoint's mix format is unreliable on some Windows
    // versions. This fixed format follows Microsoft's process-loopback sample;
    // AUTOCONVERTPCM lets the audio engine perform any needed conversion.
    WAVEFORMATEX format{};
    format.wFormatTag = WAVE_FORMAT_PCM;
    format.nChannels = 2;
    format.nSamplesPerSec = 44100;
    format.wBitsPerSample = 16;
    format.nBlockAlign = static_cast<WORD>(format.nChannels *
                                            format.wBitsPerSample / 8U);
    format.nAvgBytesPerSec = format.nSamplesPerSec * format.nBlockAlign;
    constexpr auto flags = AUDCLNT_STREAMFLAGS_LOOPBACK |
                           AUDCLNT_STREAMFLAGS_EVENTCALLBACK |
                           AUDCLNT_STREAMFLAGS_AUTOCONVERTPCM;
    if (FAILED(result = client->Initialize(AUDCLNT_SHAREMODE_SHARED, flags, 0,
                                            0, &format, nullptr))) {
      SetStatus(Status::kUnavailable,
                HResultText("Initializing Application Input", result));
      started.set_value(false);
      finish();
      return;
    }
    audio_event = CreateEventW(nullptr, FALSE, FALSE, nullptr);
    if (audio_event == nullptr ||
        FAILED(result = client->GetService(IID_PPV_ARGS(&capture))) ||
        FAILED(result = client->SetEventHandle(audio_event))) {
      SetStatus(Status::kUnavailable,
                audio_event == nullptr
                    ? "The Application Input audio event could not be created."
                    : HResultText("Preparing Application Input", result));
      started.set_value(false);
      close_event();
      finish();
      return;
    }
    UINT32 buffer_frames = 0;
    if (FAILED(result = client->GetBufferSize(&buffer_frames))) {
      SetStatus(Status::kUnavailable,
                HResultText("Reading Application Input buffer", result));
      started.set_value(false);
      close_event();
      finish();
      return;
    }
    source_rate_ = static_cast<double>(format.nSamplesPerSec);
    nominal_ratio_ = source_rate_ / target_rate_;
    ratio_ = nominal_ratio_;
    target_frames_ = static_cast<std::size_t>(std::max(
        2.0, std::round(source_rate_ * kTargetBufferSeconds)));
    if (!std::isfinite(nominal_ratio_) || nominal_ratio_ <= 0.0) {
      SetStatus(Status::kUnavailable,
                "The Application Input sample rate is invalid.");
      started.set_value(false);
      close_event();
      finish();
      return;
    }
    auto left = std::vector<float>(std::max<UINT32>(buffer_frames, 4096U));
    auto right = std::vector<float>(left.size());
    if (FAILED(result = client->Start())) {
      SetStatus(Status::kUnavailable,
                HResultText("Starting Application Input", result));
      started.set_value(false);
      close_event();
      finish();
      return;
    }
    SetStatus(Status::kActive, {});
    started.set_value(true);
    const auto handles = std::array<HANDLE, 2>{stop_event_, audio_event};
    while (true) {
      const auto wait = WaitForMultipleObjects(
          static_cast<DWORD>(handles.size()), handles.data(), FALSE, 10);
      if (wait == WAIT_OBJECT_0) {
        break;
      }
      if (wait != WAIT_OBJECT_0 + 1U && wait != WAIT_TIMEOUT) {
        SetStatus(Status::kUnavailable, "The Application Input wait failed.");
        break;
      }
      UINT32 packet_frames = 0;
      result = capture->GetNextPacketSize(&packet_frames);
      while (SUCCEEDED(result) && packet_frames > 0) {
        BYTE* data = nullptr;
        UINT32 frames = 0;
        DWORD packet_flags = 0;
        result = capture->GetBuffer(&data, &frames, &packet_flags, nullptr,
                                    nullptr);
        if (FAILED(result)) {
          break;
        }
        if ((packet_flags & AUDCLNT_BUFFERFLAGS_DATA_DISCONTINUITY) != 0) {
          discontinuities_.fetch_add(1, std::memory_order_release);
        }
        if (left.size() < frames) {
          left.resize(frames);
          right.resize(frames);
        }
        const auto silent = (packet_flags & AUDCLNT_BUFFERFLAGS_SILENT) != 0;
        for (UINT32 frame = 0; frame < frames; ++frame) {
          left[frame] = silent ? 0.0F : ReadSample(data, frame, 0, format);
          right[frame] = silent ? 0.0F : ReadSample(
              data, frame, format.nChannels > 1 ? 1U : 0U, format);
        }
        fifo_.Push(left.data(), right.data(), frames);
        result = capture->ReleaseBuffer(frames);
        if (FAILED(result)) {
          break;
        }
        result = capture->GetNextPacketSize(&packet_frames);
      }
      if (FAILED(result)) {
        SetStatus(Status::kUnavailable,
                  HResultText("Reading Application Input", result));
        break;
      }
    }
    client->Stop();
    if (GetStatus() == Status::kActive) {
      SetStatus(Status::kOff, {});
    }
    close_event();
    finish();
  }
#endif

  StatusCallback callback_;
  ProcessFifo fifo_{48000U * 4U};
  std::atomic<Status> status_{Status::kOff};
  mutable std::mutex error_mutex_;
  std::string error_;
#ifdef _WIN32
  std::thread worker_;
  HANDLE stop_event_ = nullptr;
#endif
  static constexpr auto kTargetBufferSeconds = 0.010;
  static constexpr auto kClockControlIntervalSeconds = 0.010;
  static constexpr auto kFifoSmoothingTimeSeconds = 0.250;
  static constexpr auto kClockProportionalGain = 0.12;
  static constexpr auto kClockIntegralGain = 0.02;
  static constexpr auto kMaxCorrection = 0.005;
  static constexpr auto kMaxIntegralCorrection = 0.004;
  double target_rate_ = 48000.0;
  double source_rate_ = 44100.0;
  std::size_t target_frames_ = 0;
  std::size_t control_frames_ = 0;
  double nominal_ratio_ = 1.0;
  double ratio_ = 1.0;
  double integral_ = 0.0;
  double position_ = 0.0;
  double smoothed_frames_ = 0.0;
  bool control_initialized_ = false;
  bool recovery_pending_ = false;
  bool playback_started_ = false;
  bool recovery_armed_ = false;
  std::uint64_t handled_underruns_ = 0;
  std::uint64_t handled_overflows_ = 0;
  std::uint64_t handled_discontinuities_ = 0;
  std::atomic<std::uint64_t> discontinuities_ = 0;
  bool resampler_ready_ = false;
  float current_left_ = 0.0F;
  float current_right_ = 0.0F;
  float next_left_ = 0.0F;
  float next_right_ = 0.0F;
};

ApplicationInput::ApplicationInput(StatusCallback callback)
    : impl_(std::make_unique<Impl>(std::move(callback))) {}
ApplicationInput::~ApplicationInput() = default;
auto ApplicationInput::Start(const std::uint32_t process_id,
                             const double output_sample_rate) -> bool {
  return impl_->Start(process_id, output_sample_rate);
}
void ApplicationInput::Stop() { impl_->Stop(); }
auto ApplicationInput::Read(float* const left, float* const right,
                            const std::size_t count) noexcept -> std::size_t {
  return impl_->Read(left, right, count);
}
auto ApplicationInput::GetStatus() const noexcept -> Status {
  return impl_->GetStatus();
}
auto ApplicationInput::GetLastError() const -> std::string {
  return impl_->GetLastError();
}

}  // namespace audio_bridge::audio
