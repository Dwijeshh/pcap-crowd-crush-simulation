#include "output.hpp"
#include "simulation.hpp"
#include <filesystem>
#include <iomanip>
#include <stdexcept>
#include <thread>

namespace pcap {
Output::Output(const std::string& prefix, const Config& config, const std::string& backend)
    : prefix_(prefix), config_(config), backend_(backend),
      snapshots_(prefix + "_snapshots.csv"), summary_(prefix + "_summary.csv") {
    if (!snapshots_ || !summary_) throw std::runtime_error("cannot create output files at " + prefix);
    write_snapshot_header(snapshots_);
    write_summary_header(summary_);
}
void Output::record(const State& state, int step, float time, double simulation_ms,
                    bool final_step) {
    write_summary(summary_, state, step, time, simulation_ms);
    summary_.flush();
    if (step % config_.snapshot_interval == 0 || step == config_.steps || final_step) {
        write_snapshot(snapshots_, state, step, time);
        snapshots_.flush();
    }
}
void Output::finish(double total_ms, double kernel_ms, double transfer_ms,
                    const std::string& device_name, int worker_threads, double metrics_ms) {
    std::ofstream out(prefix_ + "_run.csv");
    if (!out) throw std::runtime_error("cannot create run metadata");
    out << "backend,pedestrians,steps,snapshot_interval,seed,dt,room_width,room_height,exit_center_y,exit_width,"
           "radius,preferred_speed,mass,relaxation_time,max_speed,interaction_strength,"
           "interaction_range,body_stiffness,interaction_cutoff,wall_strength,wall_range,"
           "obstacle_x,obstacle_y,obstacle_radius,hardware_threads,device_name,total_ms,kernel_ms,transfer_ms,"
           "worker_threads,metrics_ms,metric_cell_size,congestion_density_threshold,"
           "congestion_speed_threshold,high_congestion_seconds,bottleneck_depth,bottleneck_margin\n";
    out << std::setprecision(9) << backend_ << ',' << config_.pedestrians << ',' << config_.steps
        << ',' << config_.snapshot_interval
        << ',' << config_.seed << ',' << config_.dt << ',' << config_.room_width << ','
        << config_.room_height << ',' << config_.exit_center_y << ',' << config_.exit_width
        << ',' << config_.radius << ',' << config_.preferred_speed << ',' << config_.mass
        << ',' << config_.relaxation_time << ',' << config_.max_speed << ','
        << config_.interaction_strength << ',' << config_.interaction_range << ','
        << config_.body_stiffness << ',' << config_.interaction_cutoff << ','
        << config_.wall_strength << ',' << config_.wall_range << ','
        << config_.obstacle_x << ',' << config_.obstacle_y << ',' << config_.obstacle_radius
        << ',' << std::thread::hardware_concurrency() << ",\"" << device_name << '\"'
        << ',' << total_ms << ',' << kernel_ms << ',' << transfer_ms
        << ',' << worker_threads << ',' << metrics_ms << ',' << config_.metric_cell_size
        << ',' << config_.congestion_density_threshold << ',' << config_.congestion_speed_threshold
        << ',' << config_.high_congestion_seconds << ',' << config_.bottleneck_depth
        << ',' << config_.bottleneck_margin << '\n';
}
} // namespace pcap
