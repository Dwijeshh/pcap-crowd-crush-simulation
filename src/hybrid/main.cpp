#include "cuda_backend.cuh"
#include "metrics.hpp"
#include "mpi_simulation.hpp"
#include "output.hpp"
#include <omp.h>
#include <exception>
#include <fstream>
#include <iostream>
#include <memory>
#include <stdexcept>
#include <string>
#include <utility>

namespace {
pcap::MetricAccumulator combine(const pcap::MetricAccumulator& local, MPI_Comm comm) {
    pcap::MetricAccumulator global;
    global.counts.resize(local.counts.size());
    global.speed_sums.resize(local.speed_sums.size());
    const int cells = static_cast<int>(local.counts.size());
    MPI_Allreduce(local.counts.data(), global.counts.data(), cells, MPI_INT, MPI_SUM, comm);
    MPI_Allreduce(local.speed_sums.data(), global.speed_sums.data(), cells,
                  MPI_DOUBLE, MPI_SUM, comm);
    const int local_ints[3] = {local.active, local.bottleneck, local.invalid};
    int global_ints[3] = {};
    MPI_Allreduce(local_ints, global_ints, 3, MPI_INT, MPI_SUM, comm);
    global.active = global_ints[0];
    global.bottleneck = global_ints[1];
    global.invalid = global_ints[2];
    MPI_Allreduce(&local.total_speed, &global.total_speed, 1,
                  MPI_DOUBLE, MPI_SUM, comm);
    return global;
}

struct Event {
    cudaEvent_t value = nullptr;
    Event() { pcap::cuda::check(cudaEventCreate(&value), "create CUDA event"); }
    ~Event() { if (value) cudaEventDestroy(value); }
};
}

int main(int argc, char** argv) {
    int provided = 0;
    MPI_Init_thread(&argc, &argv, MPI_THREAD_FUNNELED, &provided);
    if (provided < MPI_THREAD_FUNNELED) {
        std::cerr << "MPI_THREAD_FUNNELED is not supported\n";
        MPI_Abort(MPI_COMM_WORLD, 1);
    }
    int rank = 0, ranks = 1;
    MPI_Comm_rank(MPI_COMM_WORLD, &rank);
    MPI_Comm_size(MPI_COMM_WORLD, &ranks);
    if (argc < 3 || argc > 5) {
        if (rank == 0)
            std::cerr << "Usage: mpiexec -n R pcap_hybrid CONFIG.cfg OUTPUT_PREFIX "
                         "[BLOCK_SIZE=256] [OMP_THREADS=1]\n";
        MPI_Finalize();
        return 2;
    }
    try {
        const auto c = pcap::load_config(argv[1]);
        const int block_size = argc >= 4 ? std::stoi(argv[3]) : 256;
        const int threads = argc == 5 ? std::stoi(argv[4]) : 1;
        if (threads < 1 || threads > omp_get_num_procs())
            throw std::invalid_argument("OpenMP threads must be between 1 and available processors");
        omp_set_dynamic(0);
        int device_count = 0;
        pcap::cuda::check(cudaGetDeviceCount(&device_count), "find CUDA devices");
        if (!device_count) throw std::runtime_error("hybrid backend requires a CUDA device");
        const int device = rank % device_count;
        pcap::cuda::check(cudaSetDevice(device), "select CUDA device");
        cudaDeviceProp properties{};
        pcap::cuda::check(cudaGetDeviceProperties(&properties, device), "get CUDA device");
        if (block_size < 1 || block_size > properties.maxThreadsPerBlock)
            throw std::invalid_argument("block size exceeds device limit");

        auto current = pcap::initialize(c);
        pcap::State next = current;
        const auto layout = pcap::make_layout(c.pedestrians);
        pcap::MetricsTracker metrics(c);
        std::unique_ptr<pcap::Output> output;
        std::unique_ptr<pcap::MetricsOutput> metrics_output;
        if (rank == 0) {
            output = std::make_unique<pcap::Output>(argv[2], c, "hybrid");
            metrics_output = std::make_unique<pcap::MetricsOutput>(argv[2], c, metrics);
        }
        auto local = metrics.accumulate(current, layout.begin(), layout.end(), threads);
        metrics.sample_aggregate(combine(local, MPI_COMM_WORLD), c.pedestrians, 0);
        if (rank == 0) {
            output->record(current, 0, 0, 0);
            metrics_output->record(metrics.output());
        }

        pcap::cuda::DeviceState device_current(current.size()), device_next(current.size());
        Event start, stop;
        double update_ms = 0, kernel_ms = 0, transfer_ms = 0;
        double comm_ms = 0, metrics_ms = 0;
        MPI_Barrier(MPI_COMM_WORLD);
        for (int step = 1; step <= c.steps; ++step) {
            const double update_start = MPI_Wtime();
            double phase_start = MPI_Wtime();
            device_current.upload(current);
            transfer_ms += (MPI_Wtime() - phase_start) * 1000;

            pcap::cuda::check(cudaEventRecord(start.value), "record kernel start");
            pcap::cuda::launch_update_range(device_current.read_view(), device_next.write_view(),
                                            c.pedestrians, layout.begin(), layout.end(),
                                            c, block_size);
            pcap::cuda::check(cudaEventRecord(stop.value), "record kernel stop");
            pcap::cuda::check(cudaEventSynchronize(stop.value), "synchronize update");
            float elapsed = 0;
            pcap::cuda::check(cudaEventElapsedTime(&elapsed, start.value, stop.value),
                              "measure kernel");
            kernel_ms += elapsed;

            phase_start = MPI_Wtime();
            device_next.download_range(next, layout.begin(), layout.end());
            transfer_ms += (MPI_Wtime() - phase_start) * 1000;
            phase_start = MPI_Wtime();
            pcap::gather_updated_state(next, layout);
            comm_ms += (MPI_Wtime() - phase_start) * 1000;
            update_ms += (MPI_Wtime() - update_start) * 1000;
            std::swap(current, next);

            phase_start = MPI_Wtime();
            local = metrics.accumulate(current, layout.begin(), layout.end(), threads);
            metrics.sample_aggregate(combine(local, MPI_COMM_WORLD), c.pedestrians, step);
            metrics_ms += (MPI_Wtime() - phase_start) * 1000;
            const bool evacuated = c.stop_when_empty && pcap::active_count(current) == 0;
            if (rank == 0 && (step % c.snapshot_interval == 0 || step == c.steps || evacuated)) {
                output->record(current, step, step * c.dt, update_ms, evacuated);
                metrics_output->record(metrics.output());
            }
            MPI_Barrier(MPI_COMM_WORLD);
            if (evacuated) break;
        }

        const double local_timing[5] = {update_ms, kernel_ms, transfer_ms,
                                        comm_ms, metrics_ms};
        double worst[5] = {};
        MPI_Reduce(local_timing, worst, 5, MPI_DOUBLE, MPI_MAX, 0, MPI_COMM_WORLD);
        if (rank == 0) {
            output->finish(worst[0], worst[1], worst[2], properties.name,
                           ranks * threads, worst[4]);
            std::ofstream timings(std::string(argv[2]) + "_hybrid_timing.csv");
            if (!timings) throw std::runtime_error("cannot create hybrid timing file");
            timings << "ranks,threads_per_rank,block_size,update_ms,kernel_ms,transfer_ms,"
                       "communication_ms,metrics_ms\n"
                    << ranks << ',' << threads << ',' << block_size << ',' << worst[0]
                    << ',' << worst[1] << ',' << worst[2] << ',' << worst[3] << ','
                    << worst[4] << '\n';
            std::cout << "hybrid (" << ranks << " ranks, " << threads << " threads/rank): "
                      << c.pedestrians - pcap::active_count(current) << '/'
                      << c.pedestrians << " exited; update_ms=" << worst[0]
                      << "; metrics_ms=" << worst[4] << '\n';
        }
    } catch (const std::exception& error) {
        std::cerr << "rank " << rank << " error: " << error.what() << '\n';
        MPI_Abort(MPI_COMM_WORLD, 1);
        return 1;
    }
    MPI_Finalize();
    return 0;
}
