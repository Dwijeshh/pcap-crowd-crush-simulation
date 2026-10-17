#pragma once

#include <cstddef>
#include <cstdint>
#include <vector>

#ifdef __CUDACC__
#define PCAP_HD __host__ __device__
#else
#define PCAP_HD
#endif

namespace pcap {
// Fixed pedestrian IDs are array indices. Inactive entries remain allocated.
struct State {
    std::vector<float> x, y, vx, vy, preferred_speed, radius;
    std::vector<std::uint8_t> active;
    explicit State(std::size_t n = 0)
        : x(n), y(n), vx(n), vy(n), preferred_speed(n), radius(n), active(n, 1) {}
    std::size_t size() const { return x.size(); }
};

// The same pointer-only views are passed to the CPU updater and CUDA kernel.
struct ConstStateView {
    const float *x, *y, *vx, *vy, *preferred_speed, *radius;
    const std::uint8_t* active;
};
struct StateView {
    float *x, *y, *vx, *vy, *preferred_speed, *radius;
    std::uint8_t* active;
};
inline ConstStateView view(const State& s) {
    return {s.x.data(), s.y.data(), s.vx.data(), s.vy.data(),
            s.preferred_speed.data(), s.radius.data(), s.active.data()};
}
inline StateView view(State& s) {
    return {s.x.data(), s.y.data(), s.vx.data(), s.vy.data(),
            s.preferred_speed.data(), s.radius.data(), s.active.data()};
}
} // namespace pcap
