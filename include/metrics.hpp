#pragma once

#include "config.hpp"
#include "state.hpp"
#include <fstream>
#include <string>
#include <vector>

namespace pcap {
struct CellMetrics {
    int count = 0;
    double density = 0;
    double average_speed = 0;
    bool congested = false;
    double consecutive_seconds = 0;
    double cumulative_seconds = 0;
};

struct MetricsSnapshot {
    int step = 0;
    double time = 0;
    int active = 0, exited = 0, bottleneck_occupancy = 0, congested_cells = 0;
    double peak_density = 0, average_speed = 0, exit_flow_per_second = 0;
    double max_consecutive_seconds = 0, max_cumulative_seconds = 0;
    std::string risk_category = "low";
    std::vector<CellMetrics> cells;
};

struct MetricAccumulator {
    std::vector<int> counts;
    std::vector<double> speed_sums;
    int active = 0, bottleneck = 0, invalid = 0;
    double total_speed = 0;
};

class MetricsTracker {
public:
    explicit MetricsTracker(const Config& config);
    // Call once for step zero and after every subsequent update, not only at snapshots.
    void sample(const State& state, int step, int threads = 1);
    MetricAccumulator accumulate(const State& state, int first, int last,
                                 int threads = 1) const;
    // Complete one step from already combined rank-local accumulators.
    void sample_aggregate(const MetricAccumulator& aggregate, int pedestrians, int step);
    MetricsSnapshot output();
    int columns() const { return columns_; }
    int rows() const { return rows_; }
    double cell_area(int column, int row) const;
private:
    Config config_;
    int columns_, rows_, last_step_ = -1, last_output_step_ = 0, last_output_exited_ = 0;
    std::vector<double> consecutive_, cumulative_;
    MetricsSnapshot latest_;
};

class MetricsOutput {
public:
    MetricsOutput(const std::string& prefix, const Config& config, const MetricsTracker& tracker);
    void record(const MetricsSnapshot& metrics);
private:
    Config config_;
    const MetricsTracker& tracker_;
    std::ofstream summary_, cells_;
};
} // namespace pcap
