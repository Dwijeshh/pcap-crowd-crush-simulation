# Contributing

Bug reports and reproducibility feedback are welcome. External code and figure contributions are paused while the team prepares the research for publication. Project team members should open an issue before a major model change so everyone can agree on its scope.

## Before submitting

1. Read the [model](docs/model_specification.md), [metrics](docs/metrics_specification.md), and [experiment](docs/experiments.md) specifications for the area you plan to change.
2. Build and run the applicable tests using the commands in the [README](README.md#quick-start).
3. Keep the shared movement rule and output format consistent across backends. If you intentionally change either, update the specification and all affected implementations and comparisons.
4. Use a separate branch for your change. Keep generated binaries, local outputs, and credentials out of the pull request.

## Evidence for a change

- **Model or backend changes:** Include the scenario, configuration, command, and relevant tests. Compare exit counts and saved states with the sequential reference where applicable.
- **Metric changes:** Document the formula, units, thresholds, and output columns. Check both summary and per-cell results.
- **Performance claims:** Record hardware, compiler/toolkit versions, seed, crowd size, time steps, worker settings, warm-up, repetition count, raw runs, median, and exact timed phase. Do not compare animation or CSV writing time with movement time.
- **Research figures or manuscript changes:** Link each numerical claim to committed data or a reproducible command. State assumptions and limitations, including the one-GPU setup when relevant.

Use the [bug report](.github/ISSUE_TEMPLATE/bug_report.md) or [feature request](.github/ISSUE_TEMPLATE/feature_request.md) template when opening an issue. Team pull requests should describe the change, how it was checked, and any effect on reproducibility. Submit only material you have the right to contribute. The current repository version is not offered under an open-source license.
