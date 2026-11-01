#include "metrics.hpp"
#include <algorithm>
#include <cmath>
#include <iomanip>
#include <limits>
#include <stdexcept>
#ifdef _OPENMP
#include <omp.h>
#endif

namespace pcap {
MetricsTracker::MetricsTracker(const Config& config) : config_(config) {
    validate(config_);
    const double nx = std::ceil(double(config_.room_width) / config_.metric_cell_size);
    const double ny = std::ceil(double(config_.room_height) / config_.metric_cell_size);
    if (nx * ny > 1000000 || nx > std::numeric_limits<int>::max() ||
        ny > std::numeric_limits<int>::max())
        throw std::invalid_argument("metric grid exceeds one million cells");
    columns_ = static_cast<int>(nx);
    rows_ = static_cast<int>(ny);
    consecutive_.assign(static_cast<std::size_t>(columns_) * rows_, 0);
    cumulative_ = consecutive_;
    latest_.cells.resize(consecutive_.size());
}

double MetricsTracker::cell_area(int column, int row) const {
    const double size = config_.metric_cell_size;
    const double width = std::min(double(config_.room_width), (column + 1) * size) - column * size;
    const double height = std::min(double(config_.room_height), (row + 1) * size) - row * size;
    return width * height;
}

void MetricsTracker::sample(const State& state, int step, int threads) {
    sample_aggregate(accumulate(state, 0, static_cast<int>(state.size()), threads),
                     static_cast<int>(state.size()), step);
}

MetricAccumulator MetricsTracker::accumulate(const State& state, int first, int last,
                                             int threads) const {
    if (first < 0 || last < first || static_cast<std::size_t>(last) > state.size() ||
        threads < 1)
        throw std::invalid_argument("invalid metric range or thread count");
    const std::size_t cells = consecutive_.size();
    const int workers =
#ifdef _OPENMP
        threads;
#else
        1;
    (void)threads;
#endif
    std::vector<std::vector<int>> counts(workers, std::vector<int>(cells, 0));
    std::vector<std::vector<double>> speed_sums(workers, std::vector<double>(cells, 0));
    int active = 0, bottleneck = 0, invalid = 0;
    double total_speed = 0;
    const double size = config_.metric_cell_size;
    const double lower = config_.exit_center_y - config_.exit_width / 2.0 - config_.bottleneck_margin;
    const double upper = config_.exit_center_y + config_.exit_width / 2.0 + config_.bottleneck_margin;
#ifdef _OPENMP
#pragma omp parallel for schedule(static) num_threads(workers) reduction(+:active,bottleneck,invalid,total_speed)
#endif
    for (int i = first; i < last; ++i) {
        if (!state.active[i]) continue;
        const double x = state.x[i], y = state.y[i];
        const double speed = std::hypot(double(state.vx[i]), double(state.vy[i]));
        if (!std::isfinite(x) || !std::isfinite(y) || !std::isfinite(speed) ||
            x < 0 || x > config_.room_width || y < 0 || y > config_.room_height) {
            ++invalid;
            continue;
        }
        const int column = std::min(columns_ - 1, static_cast<int>(x / size));
        const int row = std::min(rows_ - 1, static_cast<int>(y / size));
        const std::size_t cell = static_cast<std::size_t>(row) * columns_ + column;
        int worker = 0;
#ifdef _OPENMP
        worker = omp_get_thread_num();
#endif
        ++counts[worker][cell];
        speed_sums[worker][cell] += speed;
        ++active;
        total_speed += speed;
        if (x >= config_.room_width - config_.bottleneck_depth && y >= lower && y <= upper)
            ++bottleneck;
    }
    MetricAccumulator result;
    result.counts.resize(cells);
    result.speed_sums.resize(cells);
    result.active = active;
    result.bottleneck = bottleneck;
    result.invalid = invalid;
    result.total_speed = total_speed;
    for (std::size_t k = 0; k < cells; ++k) {
        for (int worker = 0; worker < workers; ++worker) {
            result.counts[k] += counts[worker][k];
            result.speed_sums[k] += speed_sums[worker][k];
        }
    }
    return result;
}

void MetricsTracker::sample_aggregate(const MetricAccumulator& aggregate,
                                      int pedestrians, int step) {
    if (step != last_step_ + 1 || pedestrians < 0 ||
        aggregate.counts.size() != consecutive_.size() ||
        aggregate.speed_sums.size() != consecutive_.size() ||
        aggregate.active < 0 || aggregate.active > pedestrians)
        throw std::invalid_argument("invalid or nonconsecutive metric aggregate");
    if (aggregate.invalid) throw std::runtime_error("active pedestrian has invalid position or speed");

    latest_.step = step;
    latest_.time = double(step) * config_.dt;
    latest_.active = aggregate.active;
    latest_.exited = pedestrians - aggregate.active;
    latest_.bottleneck_occupancy = aggregate.bottleneck;
    latest_.congested_cells = 0;
    latest_.peak_density = 0;
    latest_.average_speed = aggregate.active ? aggregate.total_speed / aggregate.active : 0;
    latest_.max_consecutive_seconds = 0;
    latest_.max_cumulative_seconds = 0;
    latest_.risk_category = "low";
    for (std::size_t k = 0; k < consecutive_.size(); ++k) {
        auto& cell = latest_.cells[k];
        const int count = aggregate.counts[k];
        const double sum = aggregate.speed_sums[k];
        const int column = static_cast<int>(k % columns_);
        const int row = static_cast<int>(k / columns_);
        cell.count = count;
        cell.density = count / cell_area(column, row);
        cell.average_speed = count ? sum / count : 0;
        cell.congested = count > 0 &&
            cell.density >= config_.congestion_density_threshold &&
            cell.average_speed <= config_.congestion_speed_threshold;
        const double elapsed = step == 0 ? 0 : config_.dt;
        consecutive_[k] = cell.congested ? consecutive_[k] + elapsed : 0;
        if (cell.congested) cumulative_[k] += elapsed;
        cell.consecutive_seconds = consecutive_[k];
        cell.cumulative_seconds = cumulative_[k];
        latest_.peak_density = std::max(latest_.peak_density, cell.density);
        latest_.max_consecutive_seconds = std::max(latest_.max_consecutive_seconds, consecutive_[k]);
        latest_.max_cumulative_seconds = std::max(latest_.max_cumulative_seconds, cumulative_[k]);
        if (cell.congested) {
            ++latest_.congested_cells;
            latest_.risk_category = cell.consecutive_seconds >= config_.high_congestion_seconds
                ? "high" : (latest_.risk_category == "high" ? "high" : "medium");
        }
    }
    last_step_ = step;
}

MetricsSnapshot MetricsTracker::output() {
    if (last_step_ < 0) throw std::logic_error("sample metrics before output");
    MetricsSnapshot result = latest_;
    if (latest_.step > last_output_step_) {
        result.exit_flow_per_second =
            (latest_.exited - last_output_exited_) /
            (double(latest_.step - last_output_step_) * config_.dt);
    }
    last_output_step_ = latest_.step;
    last_output_exited_ = latest_.exited;
    return result;
}

MetricsOutput::MetricsOutput(const std::string& prefix, const Config& config,
                             const MetricsTracker& tracker)
    : config_(config), tracker_(tracker), summary_(prefix + "_metrics.csv"),
      cells_(prefix + "_cells.csv") {
    if (!summary_ || !cells_) throw std::runtime_error("cannot create metric files at " + prefix);
    summary_ << "step,time,active,exited,bottleneck_occupancy,peak_density,average_speed,"
                "congested_cells,max_consecutive_seconds,max_cumulative_seconds,exit_flow_per_second,"
                "risk_category,metric_cell_size,congestion_density_threshold,"
                "congestion_speed_threshold,high_congestion_seconds,bottleneck_depth,bottleneck_margin\n";
    cells_ << "step,time,column,row,count,area,density,average_speed,congested,"
              "consecutive_seconds,cumulative_seconds\n";
    summary_ << std::setprecision(10);
    cells_ << std::setprecision(10);
}

void MetricsOutput::record(const MetricsSnapshot& m) {
    summary_ << m.step << ',' << m.time << ',' << m.active << ',' << m.exited << ','
             << m.bottleneck_occupancy << ',' << m.peak_density << ',' << m.average_speed
             << ',' << m.congested_cells << ',' << m.max_consecutive_seconds << ','
             << m.max_cumulative_seconds << ',' << m.exit_flow_per_second << ','
             << m.risk_category << ',' << config_.metric_cell_size << ','
             << config_.congestion_density_threshold << ',' << config_.congestion_speed_threshold
             << ',' << config_.high_congestion_seconds << ',' << config_.bottleneck_depth << ','
             << config_.bottleneck_margin << '\n';
    summary_.flush();  // Live viewers consume each completed metric row.
    for (int row = 0; row < tracker_.rows(); ++row) {
        for (int column = 0; column < tracker_.columns(); ++column) {
            const auto& cell = m.cells[static_cast<std::size_t>(row) * tracker_.columns() + column];
            cells_ << m.step << ',' << m.time << ',' << column << ',' << row << ','
                   << cell.count << ',' << tracker_.cell_area(column, row) << ','
                   << cell.density << ',' << cell.average_speed << ',' << int(cell.congested)
                   << ',' << cell.consecutive_seconds << ',' << cell.cumulative_seconds << '\n';
        }
    }
}
} // namespace pcap
