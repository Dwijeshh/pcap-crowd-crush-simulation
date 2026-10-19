#include "metrics.hpp"
#ifdef NDEBUG
#undef NDEBUG
#endif
#include <cassert>
#include <cmath>
#include <iostream>

int main() {
    pcap::Config c;
    c.metric_cell_size = 7;
    c.congestion_density_threshold = 0.05f;
    c.congestion_speed_threshold = 0.5f;
    c.high_congestion_seconds = 0.04f;
    pcap::MetricsTracker tracker(c);
    assert(tracker.columns() == 3 && tracker.rows() == 2);
    assert(std::abs(tracker.cell_area(2, 1) - 30) < 1e-10);

    pcap::State s(2);
    s.x = {19, 19.5f}; s.y = {11, 11.5f};
    s.vx = {0.1f, 0.3f};
    tracker.sample(s, 0);
    auto m = tracker.output();
    const auto cell = std::size_t(5);
    assert(m.cells[cell].count == 2);
    assert(std::abs(m.cells[cell].density - 2.0 / 30) < 1e-10);
    assert(std::abs(m.cells[cell].average_speed - 0.2) < 1e-6);
    assert(m.cells[cell].congested && m.risk_category == "medium");
    assert(m.exit_flow_per_second == 0);

    // The hybrid backend combines independent rank-local accumulators.
    pcap::MetricsTracker partitioned(c);
    auto first = partitioned.accumulate(s, 0, 1);
    const auto second = partitioned.accumulate(s, 1, 2);
    for (std::size_t k = 0; k < first.counts.size(); ++k) {
        first.counts[k] += second.counts[k];
        first.speed_sums[k] += second.speed_sums[k];
    }
    first.active += second.active;
    first.bottleneck += second.bottleneck;
    first.invalid += second.invalid;
    first.total_speed += second.total_speed;
    partitioned.sample_aggregate(first, 2, 0);
    const auto combined = partitioned.output();
    assert(combined.active == m.active);
    assert(combined.bottleneck_occupancy == m.bottleneck_occupancy);
    assert(combined.cells[cell].count == m.cells[cell].count);
    assert(std::abs(combined.cells[cell].average_speed - m.cells[cell].average_speed) < 1e-10);

    tracker.sample(s, 1);
    m = tracker.output();
    assert(std::abs(m.cells[cell].consecutive_seconds - c.dt) < 1e-8);
    assert(m.risk_category == "medium");
    tracker.sample(s, 2);
    m = tracker.output();
    assert(std::abs(m.cells[cell].consecutive_seconds - 2 * c.dt) < 1e-8);
    assert(m.risk_category == "high");

    s.active[1] = 0;
    tracker.sample(s, 3);
    m = tracker.output();
    assert(m.active == 1 && m.exited == 1);
    assert(std::abs(m.exit_flow_per_second - 1.0 / c.dt) < 1e-4);
    assert(m.cells[cell].consecutive_seconds == 0);
    assert(std::abs(m.cells[cell].cumulative_seconds - 2 * c.dt) < 1e-8);
    assert(m.risk_category == "low");

    pcap::State empty;
    pcap::MetricsTracker empty_tracker(c);
    empty_tracker.sample(empty, 0);
    assert(empty_tracker.output().average_speed == 0);
    std::cout << "metrics tests passed\n";
}
