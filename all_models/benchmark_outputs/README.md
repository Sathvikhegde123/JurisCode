# Benchmark Outputs

This folder contains the results of various benchmarks performed on the JurisCode models.

## Files

- `claude_evaluator_prompt.txt`: Prompt used for LLM-based evaluation (using Claude).
- `run_summary.json`: High-level summary of a benchmark run.
- `combined_packfalse_packtrue_outputs.json`: Comparison of model outputs with and without sequence packing during training.
- `packtrue_outputs.json` / `packfalse_outputs.json`: Detailed outputs for specific training configurations.

## Significance

These outputs are used to quantify model performance, identify regressions, and choose the best-performing adapters for production deployment.
