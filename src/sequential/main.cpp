#include "config.hpp"
#include "output.hpp"
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
        pcap::State next(current.size());
        pcap::Output output(argv[2], c, "sequential");
        output.record(current, 0, 0, 0);
        double elapsed_ms = 0;
        for (int t = 1; t <= c.steps; ++t) {
            const auto start = std::chrono::steady_clock::now();
            pcap::step(current, next, c);
            const auto end = std::chrono::steady_clock::now();
            elapsed_ms += std::chrono::duration<double, std::milli>(end - start).count();
            std::swap(current, next);
            if (t % c.snapshot_interval == 0 || t == c.steps)
                output.record(current, t, t * c.dt, elapsed_ms);
        }
        output.finish(elapsed_ms);
        std::cout << "sequential: " << c.pedestrians - pcap::active_count(current)
                  << '/' << c.pedestrians << " exited; simulation_ms=" << elapsed_ms << '\n';
        return 0;
    } catch (const std::exception& e) {
        std::cerr << "error: " << e.what() << '\n';
        return 1;
    }
}
