#pragma once

#include "config.hpp"
#include "state.hpp"
#include <cmath>

namespace pcap {
PCAP_HD inline float clampf(float v, float lo, float hi) { return fminf(hi, fmaxf(lo, v)); }

// A deterministic direction is used for coincident centres on both devices.
PCAP_HD inline void unit(float dx, float dy, int i, int j, float& ux, float& uy, float& d) {
    d = sqrtf(dx * dx + dy * dy);
    if (d < 1e-6f) {
        ux = i < j ? -1.0f : 1.0f;
        uy = 0.0f;
        d = 1e-6f;
    } else { ux = dx / d; uy = dy / d; }
}

PCAP_HD inline void repulsion(float dx, float dy, float clearance, int i, int j,
                              float strength, float range, float stiffness,
                              float& fx, float& fy) {
    float ux, uy, d;
    unit(dx, dy, i, j, ux, uy, d);
    const float magnitude = strength * expf(clampf(-clearance / range, -20.0f, 10.0f))
                          + stiffness * fmaxf(-clearance, 0.0f);
    fx += magnitude * ux;
    fy += magnitude * uy;
}

// One agent reads only current arrays and writes only its own next-state slot.
PCAP_HD inline void update_one(int i, int n, ConstStateView cur, StateView next, const Config& c) {
    next.preferred_speed[i] = cur.preferred_speed[i];
    next.radius[i] = cur.radius[i];
    next.active[i] = cur.active[i];
    next.x[i] = cur.x[i]; next.y[i] = cur.y[i];
    next.vx[i] = cur.vx[i]; next.vy[i] = cur.vy[i];
    if (!cur.active[i]) return;

    const float r = cur.radius[i], x = cur.x[i], y = cur.y[i];
    const float lower = c.exit_center_y - c.exit_width * 0.5f;
    const float upper = c.exit_center_y + c.exit_width * 0.5f;
    const float target_y = clampf(y, lower + r, upper - r);
    float ex, ey, distance;
    unit(c.room_width - x, target_y - y, i, -i, ex, ey, distance);
    float fx = c.mass * (cur.preferred_speed[i] * ex - cur.vx[i]) / c.relaxation_time;
    float fy = c.mass * (cur.preferred_speed[i] * ey - cur.vy[i]) / c.relaxation_time;

    for (int j = 0; j < n; ++j) {
        if (j == i || !cur.active[j]) continue;
        const float dx = x - cur.x[j], dy = y - cur.y[j];
        const float d = sqrtf(dx * dx + dy * dy);
        if (d > c.interaction_cutoff) continue;
        repulsion(dx, dy, d - r - cur.radius[j], i, j,
                  c.interaction_strength, c.interaction_range, c.body_stiffness, fx, fy);
    }

    // Room walls are line segments. The right wall has an opening only at the exit.
    repulsion(1, 0, x - r, i, -1, c.wall_strength, c.wall_range, c.body_stiffness, fx, fy);
    repulsion(0, 1, y - r, i, -2, c.wall_strength, c.wall_range, c.body_stiffness, fx, fy);
    repulsion(0, -1, c.room_height - y - r, i, -3,
              c.wall_strength, c.wall_range, c.body_stiffness, fx, fy);
    if (y < lower + r || y > upper - r) {
        repulsion(-1, 0, c.room_width - x - r, i, -4,
                  c.wall_strength, c.wall_range, c.body_stiffness, fx, fy);
    }
    if (c.obstacle_radius > 0) {
        const float dx = x - c.obstacle_x, dy = y - c.obstacle_y;
        const float d = sqrtf(dx * dx + dy * dy);
        if (d <= c.interaction_cutoff + c.obstacle_radius) {
            repulsion(dx, dy, d - r - c.obstacle_radius, i, -5,
                      c.wall_strength, c.wall_range, c.body_stiffness, fx, fy);
        }
    }

    float vx = cur.vx[i] + (fx / c.mass) * c.dt;
    float vy = cur.vy[i] + (fy / c.mass) * c.dt;
    const float speed = sqrtf(vx * vx + vy * vy);
    if (speed > c.max_speed) { vx *= c.max_speed / speed; vy *= c.max_speed / speed; }
    float nx = x + vx * c.dt, ny = y + vy * c.dt;

    // The centre crosses the room boundary inside the opening with full radius.
    if (nx >= c.room_width && vx > 0) {
        const float t = (c.room_width - x) / (nx - x);
        const float crossing_y = y + t * (ny - y);
        if (crossing_y >= lower + r && crossing_y <= upper - r) {
            next.x[i] = nx; next.y[i] = ny;
            next.vx[i] = vx; next.vy[i] = vy;
            next.active[i] = 0;
            return;
        }
    }
    if (nx < r) { nx = r; vx = 0; }
    if (nx > c.room_width - r && (ny < lower + r || ny > upper - r)) {
        nx = c.room_width - r; vx = 0;
    }
    if (ny < r) { ny = r; vy = 0; }
    if (ny > c.room_height - r) { ny = c.room_height - r; vy = 0; }
    if (c.obstacle_radius > 0) {
        const float dx = nx - c.obstacle_x, dy = ny - c.obstacle_y;
        float ux, uy, d;
        unit(dx, dy, i, -5, ux, uy, d);
        const float limit = c.obstacle_radius + r;
        if (d < limit) {
            nx = c.obstacle_x + ux * limit;
            ny = c.obstacle_y + uy * limit;
            const float inward = vx * ux + vy * uy;
            if (inward < 0) { vx -= inward * ux; vy -= inward * uy; }
        }
    }
    next.x[i] = nx; next.y[i] = ny;
    next.vx[i] = vx; next.vy[i] = vy;
}
} // namespace pcap
