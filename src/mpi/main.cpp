#include "metrics.hpp"
#include "mpi_simulation.hpp"
#include "output.hpp"
#include <exception>
#include <fstream>
#include <iostream>
#include <memory>
#include <string>
#include <utility>

int main(int argc, char** argv) {
    int provided = 0;
    MPI_Init_thread(&argc, &argv, MPI_THREAD_FUNNELED, &provided);
    if (provided < MPI_THREAD_FUNNELED) {
        std::cerr << "MPI_THREAD_FUNNELED is not supported\n";
        MPI_Abort(MPI_COMM_WORLD, 1);
    }
    int rank = 0, size = 1;
    MPI_Comm_rank(MPI_COMM_WORLD, &rank);
    MPI_Comm_size(MPI_COMM_WORLD, &size);
    if (argc != 3) {
        if (rank == 0) std::cerr << "Usage: mpirun -np P pcap_mpi CONFIG.cfg OUTPUT_PREFIX\n";
        MPI_Finalize();
        return 2;
    }
    try {
        // Every rank builds the identical initial state (same seed).
        const auto c = pcap::load_config(argv[1]);
        auto current = pcap::initialize(c);
        pcap::State next = current;  // copy so constant fields exist everywhere
        const auto layout = pcap::make_layout(c.pedestrians);

        std::unique_ptr<pcap::Output> output;
        std::unique_ptr<pcap::MetricsTracker> metrics;
        std::unique_ptr<pcap::MetricsOutput> metrics_output;
        if (rank == 0) {
            output = std::make_unique<pcap::Output>(argv[2], c, "mpi");
            metrics = std::make_unique<pcap::MetricsTracker>(c);
            metrics_output = std::make_unique<pcap::MetricsOutput>(argv[2], c, *metrics);
            metrics->sample(current, 0, 1);
            output->record(current, 0, 0, 0);
            metrics_output->record(metrics->output());
        }

        pcap::MpiTiming timing;
        double update_s = 0, metrics_s = 0;
        MPI_Barrier(MPI_COMM_WORLD);
        for (int t = 1; t <= c.steps; ++t) {
            const double start = MPI_Wtime();
            pcap::step_mpi(current, next, c, layout, &timing);
            update_s += MPI_Wtime() - start;
            std::swap(current, next);
            if (rank == 0) {
                const double m0 = MPI_Wtime();
                metrics->sample(current, t, 1);
                metrics_s += MPI_Wtime() - m0;
                if (t % c.snapshot_interval == 0 || t == c.steps) {
                    output->record(current, t, static_cast<float>(t) * c.dt, update_s * 1000.0);
                    metrics_output->record(metrics->output());
                }
            }
            MPI_Barrier(MPI_COMM_WORLD);  // keeps rank 0's extra work out of timing
        }

        // Report the slowest rank for each component, as the plan requires.
        double local[4] = {update_s * 1000.0, timing.compute_s * 1000.0,
                           timing.comm_s * 1000.0, metrics_s * 1000.0};
        double worst[4] = {0, 0, 0, 0};
        MPI_Reduce(local, worst, 4, MPI_DOUBLE, MPI_MAX, 0, MPI_COMM_WORLD);
        if (rank == 0) {
            output->finish(worst[0], 0, 0, "cpu", size, worst[3]);
            std::ofstream timing_csv(std::string(argv[2]) + "_mpi_timing.csv");
            timing_csv << "ranks,update_ms,compute_ms,comm_ms,metrics_ms\n"
                       << size << ',' << worst[0] << ',' << worst[1] << ','
                       << worst[2] << ',' << worst[3] << '\n';
            std::cout << "mpi (" << size << " ranks): "
                      << c.pedestrians - pcap::active_count(current) << '/' << c.pedestrians
                      << " exited; update_ms=" << worst[0] << "; compute_ms=" << worst[1]
                      << "; comm_ms=" << worst[2] << "; metrics_ms=" << worst[3] << '\n';
        }
    } catch (const std::exception& e) {
        std::cerr << "rank " << rank << " error: " << e.what() << '\n';
        MPI_Abort(MPI_COMM_WORLD, 1);
    }
    MPI_Finalize();
    return 0;
}
