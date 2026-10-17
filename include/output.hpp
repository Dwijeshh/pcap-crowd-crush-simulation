#pragma once
#include "config.hpp"
#include "state.hpp"
#include <fstream>
#include <string>

namespace pcap {
class Output {
public:
    Output(const std::string& prefix, const Config& config, const std::string& backend);
    void record(const State& state, int step, float time, double simulation_ms);
    void finish(double total_ms, double kernel_ms = 0, double transfer_ms = 0,
                const std::string& device_name = "cpu");
private:
    std::string prefix_;
    Config config_;
    std::string backend_;
    std::ofstream snapshots_, summary_;
};
} // namespace pcap
