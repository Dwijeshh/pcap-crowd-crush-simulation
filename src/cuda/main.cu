#include "cuda_backend.cuh"
#include "output.hpp"
#include "simulation.hpp"
#include <chrono>
#include <exception>
#include <iostream>
#include <memory>
#include <stdexcept>
#include <utility>

namespace {
struct Event {
    cudaEvent_t value = nullptr;
    Event() { pcap::cuda::check(cudaEventCreate(&value), "create CUDA event"); }
    ~Event() { if (value) cudaEventDestroy(value); }
};
double milliseconds(std::chrono::steady_clock::time_point start) {
    return std::chrono::duration<double, std::milli>(std::chrono::steady_clock::now() - start).count();
}
}

int main(int argc, char** argv) {
    if (argc < 3 || argc > 4) {
        std::cerr << "Usage: pcap_cuda CONFIG.cfg OUTPUT_PREFIX [BLOCK_SIZE=256]\n";
        return 2;
    }
    try {
        const auto c = pcap::load_config(argv[1]);
        const int block_size = argc == 4 ? std::stoi(argv[3]) : 256;
        int device = 0;
        pcap::cuda::check(cudaGetDevice(&device), "find CUDA device");
        cudaDeviceProp properties{};
        pcap::cuda::check(cudaGetDeviceProperties(&properties, device), "get CUDA device properties");
        if (block_size <= 0 || block_size > properties.maxThreadsPerBlock)
            throw std::invalid_argument("block size exceeds device limit");

        auto host = pcap::initialize(c);
        pcap::Output output(argv[2], c, "cuda");
        output.record(host, 0, 0, 0);
        double transfer_ms = 0, kernel_ms = 0, total_ms = 0;
        auto segment_start = std::chrono::steady_clock::now();
        auto a = std::make_unique<pcap::cuda::DeviceState>(host.size());
        auto b = std::make_unique<pcap::cuda::DeviceState>(host.size());
        total_ms += milliseconds(segment_start);
        auto transfer_start = std::chrono::steady_clock::now();
        a->upload(host);
        const double upload_ms = milliseconds(transfer_start);
        transfer_ms += upload_ms; total_ms += upload_ms;
        Event start, stop;
        for (int t = 1; t <= c.steps; ++t) {
            if (!host.size()) break;
            segment_start = std::chrono::steady_clock::now();
            pcap::cuda::check(cudaEventRecord(start.value), "record kernel start");
            pcap::cuda::launch_update_range(a->read_view(), b->write_view(), c.pedestrians,
                                            0, c.pedestrians, c, block_size);
            pcap::cuda::check(cudaEventRecord(stop.value), "record kernel stop");
            pcap::cuda::check(cudaEventSynchronize(stop.value), "synchronize update");
            float step_ms = 0;
            pcap::cuda::check(cudaEventElapsedTime(&step_ms, start.value, stop.value), "measure kernel");
            kernel_ms += step_ms;
            total_ms += milliseconds(segment_start);
            std::swap(a, b);
            if (t % c.snapshot_interval == 0 || t == c.steps) {
                transfer_start = std::chrono::steady_clock::now();
                a->download(host);
                const double download_ms = milliseconds(transfer_start);
                transfer_ms += download_ms; total_ms += download_ms;
                output.record(host, t, t * c.dt, kernel_ms);
            }
        }
        output.finish(total_ms, kernel_ms, transfer_ms, properties.name);
        std::cout << "cuda: " << c.pedestrians - pcap::active_count(host)
                  << '/' << c.pedestrians << " exited; total_ms=" << total_ms
                  << "; kernel_ms=" << kernel_ms << "; transfer_ms=" << transfer_ms << '\n';
        return 0;
    } catch (const std::exception& e) {
        std::cerr << "error: " << e.what() << '\n';
        return 1;
    }
}
