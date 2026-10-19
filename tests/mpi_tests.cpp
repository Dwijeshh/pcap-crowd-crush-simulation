#include "mpi_simulation.hpp"
#include "simulation.hpp"
#include <iostream>
#include <utility>

namespace {
// Runs the sequential reference and the MPI version side by side and requires
// identical positions, velocities and active flags after every step.
bool run_case(const char* label, const pcap::Config& c) {
    int rank = 0;
    MPI_Comm_rank(MPI_COMM_WORLD, &rank);
    auto serial = pcap::initialize(c);
    auto parallel = serial;
    pcap::State serial_next = serial, parallel_next = serial;
    const auto layout = pcap::make_layout(c.pedestrians);
    for (int step = 1; step <= c.steps; ++step) {
        pcap::step(serial, serial_next, c);
        pcap::step_mpi(parallel, parallel_next, c, layout);
        std::swap(serial, serial_next);
        std::swap(parallel, parallel_next);
        const int same_here = serial.x == parallel.x && serial.y == parallel.y &&
                              serial.vx == parallel.vx && serial.vy == parallel.vy &&
                              serial.active == parallel.active;
        int same_everywhere = 0;
        MPI_Allreduce(&same_here, &same_everywhere, 1, MPI_INT, MPI_MIN, MPI_COMM_WORLD);
        if (!same_everywhere) {
            if (rank == 0) std::cout << "FAIL " << label << ": mismatch at step " << step << '\n';
            return false;
        }
    }
    if (rank == 0)
        std::cout << "ok   " << label << ": exited "
                  << c.pedestrians - static_cast<int>(pcap::active_count(serial)) << '/'
                  << c.pedestrians << '\n';
    return true;
}
} // namespace

int main(int argc, char** argv) {
    MPI_Init(&argc, &argv);
    int rank = 0, size = 1;
    MPI_Comm_rank(MPI_COMM_WORLD, &rank);
    MPI_Comm_size(MPI_COMM_WORLD, &size);

    pcap::Config uneven;            // odd count: uneven split on 2 and 4 ranks
    uneven.pedestrians = 301;
    uneven.steps = 600;

    pcap::Config tiny;              // fewer pedestrians than ranks: some ranks get none
    tiny.pedestrians = 3;
    tiny.steps = 300;

    pcap::Config hard;              // obstacle plus a narrow exit
    hard.pedestrians = 150;
    hard.steps = 400;
    hard.exit_width = 1.0f;
    hard.obstacle_x = 10.0f;
    hard.obstacle_y = 6.0f;
    hard.obstacle_radius = 1.0f;

    bool ok = true;
    ok = run_case("uneven split", uneven) && ok;
    ok = run_case("fewer pedestrians than ranks", tiny) && ok;
    ok = run_case("obstacle and narrow exit", hard) && ok;
    if (rank == 0) std::cout << (ok ? "MPI comparisons passed" : "MPI comparisons FAILED")
                             << " on " << size << " rank(s)\n";
    MPI_Finalize();
    return ok ? 0 : 1;
}
