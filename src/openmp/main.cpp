#include "metrics.hpp"
#include "openmp_simulation.hpp"
#include "output.hpp"
#include <chrono>
#include <exception>
#include <iostream>
#include <omp.h>
#include <stdexcept>
#include <utility>

int main(int argc, char** argv) {
    if (argc < 3 || argc > 4) {
        std::cerr << "Usage: pcap_openmp CONFIG.cfg OUTPUT_PREFIX [THREADS]\n";
        return 2;
    }
    try {
        const int threads = argc == 4 ? std::stoi(argv[3]) : omp_get_max_threads();
        if (threads < 1 || threads > omp_get_num_procs())
            throw std::invalid_argument("thread count must be between 1 and available processors");
        omp_set_dynamic(0);
        const auto c = pcap::load_config(argv[1]);
        auto current = pcap::initialize(c);
        pcap::State next(current.size());
        pcap::Output output(argv[2], c, "openmp");
        pcap::MetricsTracker metrics(c);
        pcap::MetricsOutput metrics_output(argv[2], c, metrics);
        metrics.sample(current, 0, threads);
        output.record(current, 0, 0, 0);
        metrics_output.record(metrics.output());
        double update_ms = 0, metrics_ms = 0;
        for (int t = 1; t <= c.steps; ++t) {
            const auto start = std::chrono::steady_clock::now();
            pcap::step_openmp(current, next, c, threads);
            update_ms += std::chrono::duration<double, std::milli>(
                std::chrono::steady_clock::now() - start).count();
            std::swap(current, next);
            const auto metrics_start = std::chrono::steady_clock::now();
            metrics.sample(current, t, threads);
            metrics_ms += std::chrono::duration<double, std::milli>(
                std::chrono::steady_clock::now() - metrics_start).count();
            const bool evacuated = c.stop_when_empty && pcap::active_count(current) == 0;
            if (t % c.snapshot_interval == 0 || t == c.steps || evacuated) {
                output.record(current, t, t * c.dt, update_ms, evacuated);
                metrics_output.record(metrics.output());
            }
            if (evacuated) break;
        }
        output.finish(update_ms, 0, 0, "cpu", threads, metrics_ms);
        std::cout << "openmp (" << threads << " threads): "
                  << c.pedestrians - pcap::active_count(current) << '/' << c.pedestrians
                  << " exited; update_ms=" << update_ms << "; metrics_ms=" << metrics_ms << '\n';
        return 0;
    } catch (const std::exception& e) {
        std::cerr << "error: " << e.what() << '\n';
        return 1;
    }
}
