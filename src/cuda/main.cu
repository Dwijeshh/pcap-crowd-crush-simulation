#include "cuda_backend.cuh"
#include "metrics.hpp"
#include "output.hpp"
#include "simulation.hpp"
#include <chrono>
#include <exception>
#include <iostream>
#include <memory>
#include <stdexcept>
#include <string>
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
    const bool metrics_enabled = argc < 4 || std::string(argv[argc - 1]) != "--no-metrics";
    const int positional = argc - (metrics_enabled ? 0 : 1);
    if (positional < 3 || positional > 4) {
        std::cerr << "Usage: pcap_cuda CONFIG.cfg OUTPUT_PREFIX [BLOCK_SIZE=256] [--no-metrics]\n";
        return 2;
    }
    try {
        const auto c = pcap::load_config(argv[1]);
        const int block_size = positional == 4 ? std::stoi(argv[3]) : 256;
        int device = 0;
        pcap::cuda::check(cudaGetDevice(&device), "find CUDA device");
        cudaDeviceProp properties{};
        pcap::cuda::check(cudaGetDeviceProperties(&properties, device), "get CUDA device properties");
        if (block_size <= 0 || block_size > properties.maxThreadsPerBlock)
            throw std::invalid_argument("block size exceeds device limit");

        auto host = pcap::initialize(c);
        pcap::Output output(argv[2], c, "cuda");
        std::unique_ptr<pcap::MetricsTracker> metrics;
        std::unique_ptr<pcap::MetricsOutput> metrics_output;
        if (metrics_enabled) {
            metrics = std::make_unique<pcap::MetricsTracker>(c);
            metrics_output = std::make_unique<pcap::MetricsOutput>(argv[2], c, *metrics);
            metrics->sample(host, 0);
            metrics_output->record(metrics->output());
        }
        output.record(host, 0, 0, 0);
        double transfer_ms = 0, kernel_ms = 0, total_ms = 0, metrics_ms = 0;
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
            if (metrics_enabled) {
                const auto metrics_start = std::chrono::steady_clock::now();
                a->download(host);
                metrics->sample(host, t);
                metrics_ms += milliseconds(metrics_start);
            }
            const bool check_evacuation = c.stop_when_empty && !metrics_enabled;
            if (check_evacuation) {
                transfer_start = std::chrono::steady_clock::now();
                a->download(host);
                const double download_ms = milliseconds(transfer_start);
                transfer_ms += download_ms; total_ms += download_ms;
            }
            const bool evacuated = c.stop_when_empty && pcap::active_count(host) == 0;
            if (t % c.snapshot_interval == 0 || t == c.steps || evacuated) {
                if (!metrics_enabled && !check_evacuation) {
                    transfer_start = std::chrono::steady_clock::now();
                    a->download(host);
                    const double download_ms = milliseconds(transfer_start);
                    transfer_ms += download_ms; total_ms += download_ms;
                }
                output.record(host, t, t * c.dt, kernel_ms, evacuated);
                if (metrics_enabled) metrics_output->record(metrics->output());
            }
            if (evacuated) break;
        }
        output.finish(total_ms, kernel_ms, transfer_ms, properties.name, 0, metrics_ms);
        std::cout << "cuda: " << c.pedestrians - pcap::active_count(host)
                  << '/' << c.pedestrians << " exited; total_ms=" << total_ms
                  << "; kernel_ms=" << kernel_ms << "; transfer_ms=" << transfer_ms
                  << "; metrics_ms=" << metrics_ms << '\n';
        return 0;
    } catch (const std::exception& e) {
        std::cerr << "error: " << e.what() << '\n';
        return 1;
    }
}
