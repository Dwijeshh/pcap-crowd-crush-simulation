# Scenario configurations

The `.cfg` files use one `key=value` pair per line, with `#` comments.
The parser rejects unknown and duplicate keys. Defaults and equations are in
`include/config.hpp` and `docs/model_specification.md`. The three committed
scenarios share the same seed, crowd, force constants and duration, and vary
only the exit width or obstacle. They support a controlled geometry demo.
For crowd scaling, enlarge the room or reduce body radius when required to
fit non-overlapping initial positions; record those changes with results.
The optional metric keys and their defaults are documented in
[`docs/metrics_specification.md`](../docs/metrics_specification.md).
