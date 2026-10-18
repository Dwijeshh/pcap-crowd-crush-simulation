#include "metrics.hpp"
#include "openmp_simulation.hpp"
#include "simulation.hpp"
#ifdef NDEBUG
#undef NDEBUG
#endif
#include <cassert>
#include <cmath>
#include <iostream>
#include <utility>

int main() {
    pcap::Config c;
    auto serial = pcap::initialize(c), parallel = serial;
    pcap::State serial_next(serial.size()), parallel_next(parallel.size());
    pcap::MetricsTracker serial_metrics(c), parallel_metrics(c);
    serial_metrics.sample(serial, 0);
    parallel_metrics.sample(parallel, 0, 4);
    for (int step = 1; step <= 50; ++step) {
        pcap::step(serial, serial_next, c);
        pcap::step_openmp(parallel, parallel_next, c, 4);
        std::swap(serial, serial_next);
        std::swap(parallel, parallel_next);
        assert(serial.x == parallel.x && serial.y == parallel.y);
        assert(serial.vx == parallel.vx && serial.vy == parallel.vy);
        assert(serial.active == parallel.active);
        serial_metrics.sample(serial, step);
        parallel_metrics.sample(parallel, step, 4);
    }
    const auto a = serial_metrics.output(), b = parallel_metrics.output();
    assert(a.active == b.active && a.exited == b.exited);
    assert(a.bottleneck_occupancy == b.bottleneck_occupancy);
    assert(a.congested_cells == b.congested_cells && a.risk_category == b.risk_category);
    for (std::size_t i = 0; i < a.cells.size(); ++i) {
        assert(a.cells[i].count == b.cells[i].count);
        assert(std::abs(a.cells[i].average_speed - b.cells[i].average_speed) < 1e-10);
        assert(a.cells[i].consecutive_seconds == b.cells[i].consecutive_seconds);
    }
    std::cout << "OpenMP comparisons passed\n";
}
