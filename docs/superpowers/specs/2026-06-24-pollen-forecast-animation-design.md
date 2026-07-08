# Pollen Forecast Animation Design

## Goal

Make the public forecast view behave like an operational seven-day pollen animation: users choose one of five regions, choose a pollen product, then play, pause, step, or scrub the forecast timeline without needing to understand run directories.

## Findings

The frontend already expects `products/pollen_map_forecast.json` and `products/city_forecast.json`. The server already has postprocess code that can produce those files.

The current production path is broken because the actual submitted WRF script is `runs/.../wrf/run.sbatch`, and that script only runs WRF, moves `wrfout`, and marks WRF success. A separate generated `logs/scripts/wrf_*.sh` contains only part of the intended wrapper and is not submitted. As a result, the latest `2026/0624` outputs have `wrfout` files but no product manifest or forecast JSON.

## Architecture

Keep the forecast computation flow unchanged. Treat postprocessing as a post-WRF export phase attached to the real `run.sbatch` output path and reusable as an idempotent repair command.

Server postprocessing will provide one canonical product contract:

- `products/product_manifest.json`
- `products/pollen_map_forecast.json`
- `products/city_forecast.json`
- `plots/*.png`
- `postprocess.json`
- copied `state.json` with `postprocess` state

The local backend will continue to proxy server product files. The frontend Portal will use five first-class region tabs (`Beijing`, `InnerMG`, `Shaanxi`, `Yulin`, `China`), auto-select the latest available bundle per region, preload map frames, and expose play, pause, next, previous, and seven-day timeline controls.

## UI

Use the recommended layout from the visual companion:

- Region segmented control is the first control.
- Main map/animation dominates the viewport.
- Product and status controls sit in a compact side panel.
- Playback controls and seven-day timeline sit at the bottom.
- Product/run details are visible but secondary.

## Boundaries

Do not change WPS, WRF, FNL/GFS selection, Slurm resource selection, or forecast scheduling semantics.

Server changes are limited to postprocessing export and postprocessing invocation after successful WRF output movement.

## Validation

Use parser/unit tests for product selection and timeline logic where possible. On the server, verify `postprocess_forecast.py --products-only` can generate required files from an existing completed run. Then restart the `smanager` screen service and rebuild local Docker services.
