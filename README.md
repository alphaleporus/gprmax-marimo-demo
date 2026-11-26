# gprMax A-scan explorer

A read-only marimo notebook that runs in the browser through WebAssembly. It loads two gprMax 4.0.2 runs of the same 2D scene, a metal cylinder buried in a dielectric half-space and the same half-space with no cylinder, and lets you overlay them, subtract the background, apply gain and look at the spectrum.

It is the live demo for the case study on moving gprMax from static plotting scripts to reactive marimo dashboards.

**Live:** https://alphaleporus.github.io/gprmax-marimo-demo/

## What's in here

- `ascan_demo.py` is the notebook.
- `public/cylinder_Ascan_2D.h5` and `public/cylinder_Ascan_2D_background.h5` are gprMax 4.0.2 output from `examples/gpr/basic/cylinder_Ascan_2D.in` and `gprMax/toolboxes/Marimo/examples/cylinder_Ascan_2D_background.in`.
- `public/gprmax_src/` holds the pure Python modules the notebook needs. gprMax itself needs compiled extensions that can't load in the browser, so the notebook fetches these and lays them out under their real package paths.
  - `h5_reader.py`, `processing.py`, `receiver_identity.py` and `trace_time.py` are unchanged copies from gprMax 4.0.2.
  - `utilities.py` contains only `fft_power`, copied unchanged from `gprMax/utilities/utilities.py` at the same tag.

## Run it locally

```
pip install marimo h5py numpy plotly
marimo run ascan_demo.py
```

To rebuild the WebAssembly site:

```
marimo export html-wasm ascan_demo.py -o dist --mode run
```

The full toolbox, with the progress tracker, B-scan dashboard and recipes, ships with gprMax:

```
pip install "gprMax[marimo]"
```

## License

GPL-3.0, the same as gprMax, since this repo includes code from it. gprMax is Copyright (C) 2015-2026 The University of Edinburgh, United Kingdom: https://github.com/gprMax/gprMax
