#pragma once

#include "config.hpp"
#include "state.hpp"
#include <cstddef>
#include <iosfwd>

namespace pcap {
State initialize(const Config& c);
void step(const State& current, State& next, const Config& c);
std::size_t active_count(const State& state);
void write_snapshot_header(std::ostream& out);
void write_snapshot(std::ostream& out, const State& state, int step, float time);
void write_summary_header(std::ostream& out);
void write_summary(std::ostream& out, const State& state, int step, float time,
                   double simulation_ms);
} // namespace pcap
