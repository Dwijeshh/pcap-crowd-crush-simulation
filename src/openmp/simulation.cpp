#include "openmp_simulation.hpp"
#include "model.hpp"
#include <stdexcept>

namespace pcap {
namespace {
struct UpdateContext {
    ConstStateView current;
    StateView next;
    const Config* config;
    int count;
};
#ifdef _MSC_VER
__declspec(noinline)
#endif
void update_index(int i, const UpdateContext* context) {
    update_one(i, context->count, context->current, context->next, *context->config);
}
}
void step_openmp(const State& current, State& next, const Config& config, int threads) {
    if (current.size() != next.size()) throw std::invalid_argument("state buffer sizes differ");
    if (threads < 1) throw std::invalid_argument("OpenMP thread count must be positive");
    const int n = static_cast<int>(current.size());
    const UpdateContext context{view(current), view(next), &config, n};
    const UpdateContext* data = &context;
#pragma omp parallel for schedule(static) num_threads(threads)
    for (int i = 0; i < n; ++i) update_index(i, data);
}
} // namespace pcap
