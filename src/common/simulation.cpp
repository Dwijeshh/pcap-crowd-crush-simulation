#include "simulation.hpp"
#include "model.hpp"
#include <cmath>
#include <iomanip>
#include <ostream>
#include <random>
#include <stdexcept>

namespace pcap {
State initialize(const Config& c) {
    validate(c);
    State s(static_cast<std::size_t>(c.pedestrians));
    std::mt19937 rng(c.seed);
    std::uniform_real_distribution<float> xdist(c.radius, c.room_width * 0.72f);
    std::uniform_real_distribution<float> ydist(c.radius, c.room_height - c.radius);
    for (int i = 0; i < c.pedestrians; ++i) {
        s.radius[i] = c.radius;
        s.preferred_speed[i] = c.preferred_speed;
        bool placed = false;
        for (int attempt = 0; attempt < 200000 && !placed; ++attempt) {
            const float x = xdist(rng), y = ydist(rng);
            if (c.obstacle_radius > 0 && std::hypot(x - c.obstacle_x, y - c.obstacle_y) < c.obstacle_radius + c.radius) continue;
            placed = true;
            for (int j = 0; j < i; ++j) {
                if (std::hypot(x - s.x[j], y - s.y[j]) < 2 * c.radius + 0.01f) { placed = false; break; }
            }
            if (placed) { s.x[i] = x; s.y[i] = y; }
        }
        if (!placed) throw std::runtime_error("cannot place crowd without overlap; reduce count or radius");
    }
    return s;
}

void step(const State& current, State& next, const Config& c) {
    if (current.size() != next.size()) throw std::invalid_argument("state buffer sizes differ");
    const auto a = view(current);
    const auto b = view(next);
    for (std::size_t i = 0; i < current.size(); ++i)
        update_one(static_cast<int>(i), static_cast<int>(current.size()), a, b, c);
}

std::size_t active_count(const State& s) {
    std::size_t n = 0;
    for (auto active : s.active) n += active != 0;
    return n;
}

void write_snapshot_header(std::ostream& out) { out << "step,time,id,x,y,vx,vy,preferred_speed,radius,active\n"; }
void write_snapshot(std::ostream& out, const State& s, int step_no, float time) {
    out << std::setprecision(9);
    for (std::size_t i = 0; i < s.size(); ++i)
        out << step_no << ',' << time << ',' << i << ',' << s.x[i] << ',' << s.y[i]
            << ',' << s.vx[i] << ',' << s.vy[i] << ',' << s.preferred_speed[i]
            << ',' << s.radius[i] << ',' << static_cast<int>(s.active[i]) << '\n';
}
void write_summary_header(std::ostream& out) { out << "step,time,active,exited,simulation_ms\n"; }
void write_summary(std::ostream& out, const State& s, int step_no, float time, double simulation_ms) {
    const auto active = active_count(s);
    out << step_no << ',' << time << ',' << active << ',' << s.size() - active << ',' << simulation_ms << '\n';
}
} // namespace pcap
