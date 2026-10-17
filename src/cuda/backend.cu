#include "cuda_backend.cuh"
#include "model.hpp"
#include <stdexcept>
#include <string>

namespace pcap::cuda {
void check(cudaError_t error, const char* context) {
    if (error != cudaSuccess)
        throw std::runtime_error(std::string(context) + ": " + cudaGetErrorString(error));
}

DeviceState::DeviceState(std::size_t n) : n_(n) {
    if (n == 0) return;
    try {
        check(cudaMalloc(&x_, n * sizeof(float)), "allocate x");
        check(cudaMalloc(&y_, n * sizeof(float)), "allocate y");
        check(cudaMalloc(&vx_, n * sizeof(float)), "allocate vx");
        check(cudaMalloc(&vy_, n * sizeof(float)), "allocate vy");
        check(cudaMalloc(&preferred_speed_, n * sizeof(float)), "allocate preferred_speed");
        check(cudaMalloc(&radius_, n * sizeof(float)), "allocate radius");
        check(cudaMalloc(&active_, n * sizeof(std::uint8_t)), "allocate active");
    } catch (...) {
        cudaFree(x_); cudaFree(y_); cudaFree(vx_); cudaFree(vy_);
        cudaFree(preferred_speed_); cudaFree(radius_); cudaFree(active_);
        throw;
    }
}
DeviceState::~DeviceState() {
    cudaFree(x_); cudaFree(y_); cudaFree(vx_); cudaFree(vy_);
    cudaFree(preferred_speed_); cudaFree(radius_); cudaFree(active_);
}
void DeviceState::upload(const State& s) {
    if (s.size() != n_) throw std::invalid_argument("device upload size mismatch");
    if (!n_) return;
#define UPLOAD(field, type) check(cudaMemcpy(field##_, s.field.data(), n_ * sizeof(type), cudaMemcpyHostToDevice), "upload " #field)
    UPLOAD(x, float); UPLOAD(y, float); UPLOAD(vx, float); UPLOAD(vy, float);
    UPLOAD(preferred_speed, float); UPLOAD(radius, float); UPLOAD(active, std::uint8_t);
#undef UPLOAD
}
void DeviceState::download(State& s) const {
    if (s.size() != n_) throw std::invalid_argument("device download size mismatch");
    if (!n_) return;
#define DOWNLOAD(field, type) check(cudaMemcpy(s.field.data(), field##_, n_ * sizeof(type), cudaMemcpyDeviceToHost), "download " #field)
    DOWNLOAD(x, float); DOWNLOAD(y, float); DOWNLOAD(vx, float); DOWNLOAD(vy, float);
    DOWNLOAD(preferred_speed, float); DOWNLOAD(radius, float); DOWNLOAD(active, std::uint8_t);
#undef DOWNLOAD
}
ConstStateView DeviceState::read_view() const {
    return {x_, y_, vx_, vy_, preferred_speed_, radius_, active_};
}
StateView DeviceState::write_view() const {
    return {x_, y_, vx_, vy_, preferred_speed_, radius_, active_};
}

__global__ void update_kernel(ConstStateView current, StateView next, int n,
                              int first, int last, Config config) {
    const int i = first + blockIdx.x * blockDim.x + threadIdx.x;
    if (i < last && i < n) update_one(i, n, current, next, config);
}
void launch_update_range(ConstStateView current, StateView next, int n,
                         int first, int last, const Config& config,
                         int block_size, cudaStream_t stream) {
    if (first < 0 || last < first || last > n || block_size <= 0 || block_size > 1024)
        throw std::invalid_argument("invalid CUDA update range or block size");
    if (first == last) return;
    update_kernel<<<(last - first + block_size - 1) / block_size, block_size, 0, stream>>>
        (current, next, n, first, last, config);
    check(cudaGetLastError(), "launch update kernel");
}
} // namespace pcap::cuda
