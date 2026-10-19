#pragma once

#include "simulation.hpp"

namespace pcap {
void step_openmp(const State& current, State& next, const Config& config, int threads);
}
