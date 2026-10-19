#include "config.hpp"
#include "output.hpp"
#include "metrics.hpp"
#include "simulation.hpp"
#include <chrono>
#include <exception>
#include <iostream>
#include <utility>

int main(int argc, char** argv) {
    if (argc != 3) {
        std::cerr << "Usage: pcap_sequential CONFIG.cfg OUTPUT_PREFIX\n";
        return 2;
    }
    try {
        const auto c = pcap::load_config(argv[1]);
        auto current = pcap::initialize(c);
        const auto allocation_start = std::chrono::steady_clock::now();
        pcap::State next(current.size());
        double total_ms = std::chrono::duration<double, std::milli>(
            std::chrono::steady_clock::now() - allocation_start).count();
        pcap::Output output(argv[2], c, "sequential");
        pcap::MetricsTracker metrics(c);
        pcap::MetricsOutput metrics_output(argv[2], c, metrics);
        metrics.sample(current, 0);
        output.record(current, 0, 0, 0);
        metrics_output.record(metrics.output());
        double elapsed_ms = 0, metrics_ms = 0;
        for (int t = 1; t <= c.steps; ++t) {
            const auto start = std::chrono::steady_clock::now();
            pcap::step(current, next, c);
            const auto end = std::chrono::steady_clock::now();
            const double step_ms = std::chrono::duration<double, std::milli>(end - start).count();
            elapsed_ms += step_ms;
            total_ms += step_ms;
            std::swap(current, next);
            const auto metrics_start = std::chrono::steady_clock::now();
            metrics.sample(current, t);
            metrics_ms += std::chrono::duration<double, std::milli>(
                std::chrono::steady_clock::now() - metrics_start).count();
            if (t % c.snapshot_interval == 0 || t == c.steps) {
                output.record(current, t, t * c.dt, elapsed_ms);
                metrics_output.record(metrics.output());
            }
        }
        output.finish(elapsed_ms, 0, 0, "cpu", 1, metrics_ms);
        std::cout << "sequential: " << c.pedestrians - pcap::active_count(current)
                  << '/' << c.pedestrians << " exited; total_ms=" << total_ms
                  << "; simulation_ms=" << elapsed_ms << '\n';
        return 0;
    } catch (const std::exception& e) {
        std::cerr << "error: " << e.what() << '\n';
        return 1;
    }
}
