#pragma once

#include <cstdint>
#include <string>

namespace pcap {
struct Config {
    int pedestrians = 100;
    int steps = 500;
    int snapshot_interval = 10;
    std::uint32_t seed = 42;
    float dt = 0.02f;
    float room_width = 20.0f, room_height = 12.0f;
    float exit_center_y = 6.0f, exit_width = 2.0f;
    float radius = 0.22f, preferred_speed = 1.3f;
    float mass = 80.0f, relaxation_time = 0.5f, max_speed = 2.5f;
    float interaction_strength = 200.0f, interaction_range = 0.35f;
    float body_stiffness = 1200.0f, interaction_cutoff = 2.0f;
    float wall_strength = 200.0f, wall_range = 0.25f;
    float obstacle_x = -1.0f, obstacle_y = -1.0f, obstacle_radius = 0.0f;
};
Config load_config(const std::string& path);
void validate(const Config& c);
} // namespace pcap
