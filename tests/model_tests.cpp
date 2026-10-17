#include "model.hpp"
#include "simulation.hpp"
#ifdef NDEBUG
#undef NDEBUG // Run model checks even in Release builds.
#endif
#include <cassert>
#include <cmath>
#include <iostream>
#include <utility>

namespace {
void run_steps(pcap::State& current, const pcap::Config& c, int count) {
    pcap::State next(current.size());
    for (int i = 0; i < count; ++i) { pcap::step(current, next, c); std::swap(current, next); }
}
}
int main() {
    pcap::Config c;
    c.pedestrians = 0;
    auto empty = pcap::initialize(c);
    pcap::State empty_next;
    pcap::step(empty, empty_next, c);
    assert(pcap::active_count(empty) == 0);

    c.pedestrians = 1;
    pcap::State one(1);
    one.x[0] = c.room_width - 0.6f;
    one.y[0] = c.exit_center_y;
    one.radius[0] = c.radius;
    one.preferred_speed[0] = c.preferred_speed;
    run_steps(one, c, 100);
    assert(one.active[0] == 0 && one.x[0] >= c.room_width);
    const float exited_x = one.x[0];
    run_steps(one, c, 2);
    assert(one.x[0] == exited_x);

    pcap::State pair(2), pair_next(2), solo(2), solo_next(2);
    pair.x = {5, 5.55f}; pair.y = {6, 6};
    pair.radius = {c.radius, c.radius};
    pair.preferred_speed = {c.preferred_speed, c.preferred_speed};
    solo = pair; solo.active[1] = 0;
    pcap::step(pair, pair_next, c);
    pcap::step(solo, solo_next, c);
    assert(pair_next.vx[0] < solo_next.vx[0]);
    pair.x[1] = pair.x[0]; pair.y[1] = pair.y[0];
    pcap::step(pair, pair_next, c);
    assert(std::isfinite(pair_next.x[0]) && std::isfinite(pair_next.x[1]));
    assert(pair_next.vx[0] < pair_next.vx[1]);

    pcap::State wall(1), wall_next(1);
    wall.x[0] = 1; wall.y[0] = c.radius;
    wall.vy[0] = -2; wall.radius[0] = c.radius;
    wall.preferred_speed[0] = c.preferred_speed;
    pcap::step(wall, wall_next, c);
    assert(wall_next.y[0] >= c.radius && std::isfinite(wall_next.vy[0]));
    wall.x[0] = c.room_width - c.radius;
    wall.y[0] = 1;
    wall.vx[0] = 2; wall.vy[0] = 0;
    pcap::step(wall, wall_next, c);
    assert(wall_next.active[0] && wall_next.x[0] <= c.room_width - c.radius);

    pcap::State regular(1), smaller(1);
    regular.x[0] = smaller.x[0] = 5;
    regular.y[0] = smaller.y[0] = c.exit_center_y;
    regular.radius[0] = smaller.radius[0] = c.radius;
    regular.preferred_speed[0] = smaller.preferred_speed[0] = c.preferred_speed;
    run_steps(regular, c, 50);
    auto fine = c; fine.dt = 0.01f;
    run_steps(smaller, fine, 100);
    assert(std::abs(regular.x[0] - smaller.x[0]) < 0.05f);

    c.pedestrians = 100;
    auto a = pcap::initialize(c), b = pcap::initialize(c);
    assert(a.x == b.x && a.y == b.y);
    for (int i = 0; i < c.pedestrians; ++i)
        for (int j = i + 1; j < c.pedestrians; ++j)
            assert(std::hypot(a.x[i] - a.x[j], a.y[i] - a.y[j]) >= 2 * c.radius);
    run_steps(a, c, 50);
    run_steps(b, c, 50);
    assert(a.x == b.x && a.y == b.y && a.active == b.active);
    for (int i = 0; i < c.pedestrians; ++i) {
        if (!a.active[i]) continue;
        assert(std::isfinite(a.x[i]) && std::isfinite(a.y[i]));
        assert(a.x[i] >= c.radius && a.x[i] <= c.room_width - c.radius);
        assert(a.y[i] >= c.radius && a.y[i] <= c.room_height - c.radius);
    }
    std::cout << "model tests passed\n";
}
