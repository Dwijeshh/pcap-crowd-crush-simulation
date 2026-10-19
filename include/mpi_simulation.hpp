#pragma once

#include "simulation.hpp"
#include <mpi.h>
#include <vector>

namespace pcap {
// Which pedestrian IDs this rank updates. Block split, handles uneven counts.
struct MpiLayout {
    int rank = 0;
    int size = 1;
    std::vector<int> counts;
    std::vector<int> displs;
    int begin() const { return displs[rank]; }
    int end() const { return displs[rank] + counts[rank]; }
};

// Wall-clock seconds spent in each phase, summed over calls.
struct MpiTiming {
    double compute_s = 0.0;
    double comm_s = 0.0;
};

MpiLayout make_layout(int pedestrians, MPI_Comm comm = MPI_COMM_WORLD);
void gather_updated_state(State& next, const MpiLayout& layout,
                          MPI_Comm comm = MPI_COMM_WORLD);

// `next` must start as a copy of `current` so constant fields are present
// for pedestrians owned by other ranks.
void step_mpi(const State& current, State& next, const Config& config,
              const MpiLayout& layout, MpiTiming* timing = nullptr,
              MPI_Comm comm = MPI_COMM_WORLD);
} // namespace pcap
