#include "mpi_simulation.hpp"
#include "model.hpp"
#include <stdexcept>

namespace pcap {
MpiLayout make_layout(int pedestrians, MPI_Comm comm) {
    MpiLayout layout;
    MPI_Comm_rank(comm, &layout.rank);
    MPI_Comm_size(comm, &layout.size);
    layout.counts.assign(layout.size, 0);
    layout.displs.assign(layout.size, 0);
    const int base = pedestrians / layout.size;
    const int remainder = pedestrians % layout.size;
    int offset = 0;
    for (int r = 0; r < layout.size; ++r) {
        layout.counts[r] = base + (r < remainder ? 1 : 0);
        layout.displs[r] = offset;
        offset += layout.counts[r];
    }
    return layout;
}

namespace {
void gather_floats(std::vector<float>& a, const MpiLayout& layout, MPI_Comm comm) {
    MPI_Allgatherv(MPI_IN_PLACE, 0, MPI_FLOAT, a.data(), layout.counts.data(),
                   layout.displs.data(), MPI_FLOAT, comm);
}
void gather_bytes(std::vector<std::uint8_t>& a, const MpiLayout& layout, MPI_Comm comm) {
    MPI_Allgatherv(MPI_IN_PLACE, 0, MPI_UNSIGNED_CHAR, a.data(), layout.counts.data(),
                   layout.displs.data(), MPI_UNSIGNED_CHAR, comm);
}
} // namespace

void gather_updated_state(State& next, const MpiLayout& layout, MPI_Comm comm) {
    const int n = static_cast<int>(next.size());
    if (layout.displs.empty() ||
        layout.displs.back() + layout.counts.back() != n)
        throw std::invalid_argument("MPI layout does not match the pedestrian count");
    gather_floats(next.x, layout, comm);
    gather_floats(next.y, layout, comm);
    gather_floats(next.vx, layout, comm);
    gather_floats(next.vy, layout, comm);
    gather_bytes(next.active, layout, comm);
}

void step_mpi(const State& current, State& next, const Config& config,
              const MpiLayout& layout, MpiTiming* timing, MPI_Comm comm) {
    if (current.size() != next.size()) throw std::invalid_argument("state buffer sizes differ");
    const int n = static_cast<int>(current.size());
    if (layout.displs.empty() ||
        layout.displs.back() + layout.counts.back() != n)
        throw std::invalid_argument("MPI layout does not match the pedestrian count");
    const ConstStateView cur = view(current);
    const StateView nxt = view(next);
    const double t0 = MPI_Wtime();
    for (int i = layout.begin(); i < layout.end(); ++i) update_one(i, n, cur, nxt, config);
    const double t1 = MPI_Wtime();
    gather_updated_state(next, layout, comm);
    const double t2 = MPI_Wtime();

    if (timing) {
        timing->compute_s += t1 - t0;
        timing->comm_s += t2 - t1;
    }
}
} // namespace pcap
