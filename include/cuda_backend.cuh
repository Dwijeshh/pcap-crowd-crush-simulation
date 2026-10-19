#pragma once
#include "config.hpp"
#include "state.hpp"
#include <cuda_runtime.h>
#include <cstddef>

namespace pcap::cuda {
void check(cudaError_t error, const char* context);

// Both buffers are SoA on the device. The hybrid backend can use the same
// launch_update_range entry point for its MPI-owned pedestrian ID interval.
class DeviceState {
public:
    explicit DeviceState(std::size_t n);
    ~DeviceState();
    DeviceState(const DeviceState&) = delete;
    DeviceState& operator=(const DeviceState&) = delete;
    DeviceState(DeviceState&&) = delete;
    DeviceState& operator=(DeviceState&&) = delete;
    void upload(const State& host);
    void download(State& host) const;
    void download_range(State& host, int first, int last) const;
    ConstStateView read_view() const;
    StateView write_view() const;
    std::size_t size() const { return n_; }
private:
    std::size_t n_;
    float *x_ = nullptr, *y_ = nullptr, *vx_ = nullptr, *vy_ = nullptr;
    float *preferred_speed_ = nullptr, *radius_ = nullptr;
    std::uint8_t* active_ = nullptr;
};

void launch_update_range(ConstStateView current, StateView next, int n,
                         int first, int last, const Config& config,
                         int block_size, cudaStream_t stream = 0);
} // namespace pcap::cuda
