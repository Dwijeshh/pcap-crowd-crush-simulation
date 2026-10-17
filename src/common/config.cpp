#include "config.hpp"
#include <cmath>
#include <fstream>
#include <map>
#include <stdexcept>

namespace pcap {
void validate(const Config& c) {
    auto positive = [](float v) { return std::isfinite(v) && v > 0; };
    if (c.pedestrians < 0 || c.steps < 0 || c.snapshot_interval <= 0 ||
        !positive(c.dt) || !positive(c.room_width) || !positive(c.room_height) ||
        !positive(c.exit_width) || c.exit_width > c.room_height ||
        !positive(c.radius) || !positive(c.preferred_speed) || !positive(c.mass) ||
        !positive(c.relaxation_time) || !positive(c.max_speed) ||
        !positive(c.interaction_strength) || !positive(c.interaction_range) ||
        !positive(c.body_stiffness) || !positive(c.interaction_cutoff) ||
        !positive(c.wall_strength) || !positive(c.wall_range) ||
        !std::isfinite(c.exit_center_y) || !std::isfinite(c.obstacle_radius) ||
        c.obstacle_radius < 0 || c.exit_width <= 2 * c.radius ||
        c.exit_center_y - c.exit_width / 2 < 0 ||
        c.exit_center_y + c.exit_width / 2 > c.room_height ||
        c.room_width <= 2 * c.radius || c.room_height <= 2 * c.radius)
        throw std::invalid_argument("invalid or inconsistent scenario parameters");
    if (c.obstacle_radius > 0 &&
        (!std::isfinite(c.obstacle_x) || !std::isfinite(c.obstacle_y) ||
         c.obstacle_x - c.obstacle_radius < c.radius ||
         c.obstacle_x + c.obstacle_radius > c.room_width - c.radius ||
         c.obstacle_y - c.obstacle_radius < c.radius ||
         c.obstacle_y + c.obstacle_radius > c.room_height - c.radius))
        throw std::invalid_argument("obstacle needs pedestrian clearance from room walls");
}

Config load_config(const std::string& path) {
    std::ifstream in(path);
    if (!in) throw std::runtime_error("cannot open configuration: " + path);
    Config c;
    std::map<std::string, double> values;
    std::string line;
    int line_no = 0;
    while (std::getline(in, line)) {
        ++line_no;
        const auto comment = line.find('#');
        if (comment != std::string::npos) line.resize(comment);
        const auto eq = line.find('=');
        if (line.find_first_not_of(" \t\r\n") == std::string::npos) continue;
        if (eq == std::string::npos) throw std::runtime_error("expected key=value at line " + std::to_string(line_no));
        auto trim = [](std::string s) {
            const auto a = s.find_first_not_of(" \t\r\n");
            if (a == std::string::npos) return std::string{};
            const auto b = s.find_last_not_of(" \t\r\n");
            return s.substr(a, b - a + 1);
        };
        const std::string key = trim(line.substr(0, eq)), raw = trim(line.substr(eq + 1));
        std::size_t consumed = 0;
        double value;
        try { value = std::stod(raw, &consumed); }
        catch (...) { throw std::runtime_error("invalid number at line " + std::to_string(line_no)); }
        if (consumed != raw.size() || !std::isfinite(value) || !values.emplace(key, value).second)
            throw std::runtime_error("invalid or duplicate value at line " + std::to_string(line_no));
    }
    auto setf = [&](const char* key, float& target) { auto it = values.find(key); if (it != values.end()) { target = static_cast<float>(it->second); values.erase(it); } };
    auto seti = [&](const char* key, int& target) { auto it = values.find(key); if (it != values.end()) { if (it->second != std::floor(it->second) || it->second < -2147483648.0 || it->second > 2147483647.0) throw std::runtime_error("invalid integer: " + std::string(key)); target = static_cast<int>(it->second); values.erase(it); } };
    seti("pedestrians", c.pedestrians); seti("steps", c.steps); seti("snapshot_interval", c.snapshot_interval);
    auto seed = values.find("seed");
    if (seed != values.end()) { if (seed->second != std::floor(seed->second) || seed->second < 0 || seed->second > 4294967295.0) throw std::runtime_error("invalid seed"); c.seed = static_cast<std::uint32_t>(seed->second); values.erase(seed); }
    setf("dt", c.dt); setf("room_width", c.room_width); setf("room_height", c.room_height);
    setf("exit_center_y", c.exit_center_y); setf("exit_width", c.exit_width);
    setf("radius", c.radius); setf("preferred_speed", c.preferred_speed);
    setf("mass", c.mass); setf("relaxation_time", c.relaxation_time); setf("max_speed", c.max_speed);
    setf("interaction_strength", c.interaction_strength); setf("interaction_range", c.interaction_range);
    setf("body_stiffness", c.body_stiffness); setf("interaction_cutoff", c.interaction_cutoff);
    setf("wall_strength", c.wall_strength); setf("wall_range", c.wall_range);
    setf("obstacle_x", c.obstacle_x); setf("obstacle_y", c.obstacle_y); setf("obstacle_radius", c.obstacle_radius);
    if (!values.empty()) throw std::runtime_error("unknown configuration key: " + values.begin()->first);
    validate(c);
    return c;
}
} // namespace pcap
