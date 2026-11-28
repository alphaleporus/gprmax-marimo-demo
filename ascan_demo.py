# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "h5py",
#     "marimo>=0.23.8",
#     "numpy",
#     "plotly",
# ]
# ///

import marimo

__generated_with = "0.26.0"
app = marimo.App(width="medium", app_title="gprMax A-scan explorer")


@app.cell(hide_code=True)
def _(mo):
    mo.md("""
    # gprMax A-scan explorer

    Two gprMax runs of the same 2D scene: a metal cylinder buried in a
    dielectric half-space, and the same half-space with no cylinder in it.
    Pick field components, overlay the runs, subtract the background,
    apply gain, or switch to the spectrum.

    Everything runs in your browser, so the first load takes up to half a
    minute while Python starts. The output files were produced by gprMax
    4.0.2 and are read with the same `h5_reader` and `processing` modules
    that ship in `gprMax[marimo]`.
    """)


@app.cell
def _():
    import sys
    from pathlib import Path

    import h5py  # noqa: F401  # used by h5_reader; imported here so WASM installs it
    import marimo as mo
    import numpy as np
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots

    return Path, go, make_subplots, mo, np, sys


@app.cell
async def _(Path, mo, sys):
    # gprMax itself needs compiled extensions, so in the browser the pure
    # Python toolbox modules are fetched from public/ and laid out under the
    # same package paths they use in a real install.
    MODULES = {
        "gprMax/toolboxes/Marimo/h5_reader.py": "h5_reader.py",
        "gprMax/toolboxes/Marimo/processing.py": "processing.py",
        "gprMax/toolboxes/Utilities/receiver_identity.py": "receiver_identity.py",
        "gprMax/toolboxes/Utilities/trace_time.py": "trace_time.py",
        "gprMax/utilities/utilities.py": "utilities.py",
    }
    DATA_FILES = ["cylinder_Ascan_2D.h5", "cylinder_Ascan_2D_background.h5"]

    public = mo.notebook_location() / "public"
    in_browser = sys.platform == "emscripten"

    async def read_bytes(relative):
        # Local runs and molab have the repo files on disk; a static WASM
        # export serves them over HTTP next to index.html.
        for candidate in (Path(str(public / relative)), Path("public") / relative):
            if candidate.is_file():
                return candidate.read_bytes()
        if not in_browser:
            raise FileNotFoundError(str(public / relative))
        from pyodide.http import pyfetch

        response = await pyfetch(str(public / relative))
        if not response.ok:
            raise FileNotFoundError(f"{relative}: HTTP {response.status}")
        return await response.bytes()

    workdir = Path("/tmp/gprmax_ascan_demo")
    for target, source in MODULES.items():
        dest = workdir / target
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(await read_bytes(f"gprmax_src/{source}"))
    for package in ["gprMax", "gprMax/toolboxes", "gprMax/toolboxes/Marimo",
                    "gprMax/toolboxes/Utilities", "gprMax/utilities"]:
        (workdir / package / "__init__.py").touch()

    data_paths = []
    for name in DATA_FILES:
        dest = workdir / "data" / name
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(await read_bytes(name))
        data_paths.append(dest)

    if str(workdir) not in sys.path:
        sys.path.insert(0, str(workdir))
    return (data_paths,)


@app.cell
def _(data_paths):
    from gprMax.toolboxes.Marimo import h5_reader, processing

    files = h5_reader.load_files(data_paths)
    target_key, background_key = (p.name for p in data_paths)
    return background_key, files, h5_reader, processing, target_key


@app.cell
def _(files, h5_reader, mo, np, target_key):
    target_file = files[target_key]
    components = h5_reader.list_components(target_file, "rx1")

    def _label(comp):
        trace = h5_reader.get_trace(target_file, comp, "rx1")
        return f"{comp} (all zeros in this 2D model)" if not np.any(trace) else comp

    default_components = [c for c in ("Ez", "Hx") if c in components] or components[:1]

    component_picker = mo.ui.multiselect(
        options={_label(c): c for c in components},
        value=[_label(c) for c in default_components],
        label="Field components",
    )
    run_picker = mo.ui.multiselect(
        options=["Target", "Background", "Target minus background"],
        value=["Target", "Background", "Target minus background"],
        label="Runs",
    )
    view_picker = mo.ui.radio(
        options=["Time domain", "Spectrum"], value="Time domain", inline=True
    )
    return component_picker, run_picker, target_file, view_picker


@app.cell
def _(mo, processing):
    gain_kind = mo.ui.dropdown(
        options={info["label"]: kind for kind, info in processing.GAIN_KINDS.items()},
        value=processing.GAIN_KINDS["none"]["label"],
        label="Gain",
    )
    return (gain_kind,)


@app.cell
def _(gain_kind, mo, processing):
    # rebuilt when the gain type changes so each slider carries the right unit
    gain_info = processing.GAIN_KINDS[gain_kind.value]
    factor_unit = gain_info["factor_unit"]
    gain_factor = mo.ui.slider(
        0.0, 5.0, step=0.1, value=1.0, debounce=True, show_value=True,
        label=f"Factor ({factor_unit})" if factor_unit else "Factor",
    )
    gain_power = mo.ui.slider(
        0.0, 3.0, step=0.1, value=1.0, debounce=True, show_value=True, label="Power"
    )
    gain_start = mo.ui.slider(
        0.0, 3.0, step=0.05, value=1.4, debounce=True, show_value=True, label="Start (ns)"
    )
    uses_factor = gain_kind.value not in ("none", "power")
    uses_power = bool(gain_info["uses_power"])
    return gain_factor, gain_power, gain_start, uses_factor, uses_power


@app.cell
def _(
    component_picker,
    gain_factor,
    gain_kind,
    gain_power,
    gain_start,
    mo,
    run_picker,
    uses_factor,
    uses_power,
    view_picker,
):
    gain_sliders = []
    if gain_kind.value != "none":
        if uses_factor:
            gain_sliders.append(gain_factor)
        if uses_power:
            gain_sliders.append(gain_power)
        gain_sliders.append(gain_start)
    controls = mo.vstack(
        [
            mo.hstack([component_picker, run_picker], justify="start", gap=2, wrap=True),
            mo.hstack([gain_kind, view_picker], justify="start", gap=2, wrap=True),
            mo.hstack(gain_sliders, justify="start", gap=2, wrap=True),
        ],
        gap=0.75,
    )
    return (controls,)


@app.cell
def _(
    background_key,
    component_picker,
    files,
    gain_factor,
    gain_kind,
    gain_power,
    gain_start,
    go,
    h5_reader,
    make_subplots,
    mo,
    np,
    processing,
    run_picker,
    target_key,
    view_picker,
):
    selected_components = component_picker.value
    selected_runs = run_picker.value
    spectrum = view_picker.value == "Spectrum"

    def _build():
        target = files[target_key]
        background = files[background_key]
        styles = {
            "Background": {"color": "#c42b91", "width": 1.6, "dash": "dash"},
            "Target": {"color": "#3b8cff", "width": 1.6},
            "Target minus background": {"color": "#28367f", "width": 2.4},
        }
        # background first so the target trace draws on top of it
        runs_in_order = [r for r in styles if r in selected_runs]
        notes = []
        view_limits = []

        fig = make_subplots(
            rows=len(selected_components),
            cols=1,
            shared_xaxes=True,
            vertical_spacing=0.08,
            subplot_titles=selected_components,
        )

        for row, comp in enumerate(selected_components, start=1):
            time_ns = h5_reader.get_time_axis(target, "ns", "rx1", comp)
            dt = target["receivers"]["rx1"]["component_meta"][comp]["sample_interval"]
            t_trace = h5_reader.get_trace(target, comp, "rx1")
            b_trace = h5_reader.get_trace(background, comp, "rx1")
            series = {"Target": t_trace, "Background": b_trace}
            if "Target minus background" in selected_runs:
                series["Target minus background"] = processing.subtract_traces(
                    t_trace,
                    b_trace,
                    dt_target=dt,
                    dt_reference=background["receivers"]["rx1"]["component_meta"][comp][
                        "sample_interval"
                    ],
                )

            x_limit = None
            for run in runs_in_order:
                trace, _curve = processing.apply_gain(
                    series[run],
                    time_ns,
                    gain_kind.value,
                    factor=gain_factor.value,
                    power=gain_power.value,
                    start_ns=gain_start.value,
                )
                if spectrum:
                    # zero-pad so the 3 ns trace gives a smooth spectrum instead of
                    # 0.33 GHz steps; the transform is still gprMax's fft_power
                    padded = np.pad(trace, (0, max(0, 4096 - trace.size)))
                    freqs, power_db, peak_db = processing.fft_spectrum(padded, dt)
                    if peak_db is None:
                        notes.append(f"{comp} {run.lower()} is all zeros, so it has no spectrum.")
                        continue
                    x = freqs / 1e9
                    y = power_db + peak_db
                    limit = processing.spectrum_view_limit(freqs, power_db) / 1e9
                    x_limit = max(x_limit or 0.0, limit)
                else:
                    x, y = time_ns, trace

                fig.add_trace(
                    go.Scatter(
                        x=x,
                        y=y,
                        mode="lines",
                        name=run,
                        legendgroup=run,
                        showlegend=row == 1,
                        line=styles[run],
                    ),
                    row=row,
                    col=1,
                )

            unit = "Power (dB)" if spectrum else h5_reader.get_unit_label(comp)
            fig.update_yaxes(title_text=unit, row=row, col=1)
            if spectrum and x_limit:
                view_limits.append(x_limit)

        if view_limits:
            # the rows share one x axis, so give every row the same fixed range
            fig.update_xaxes(range=[0, max(view_limits)], autorange=False)
        fig.update_xaxes(
            title_text="Frequency (GHz)" if spectrum else "Time (ns)",
            row=len(selected_components),
            col=1,
        )
        fig.update_layout(
            uirevision=f"{view_picker.value}-{','.join(selected_components)}",
            height=260 * len(selected_components) + 80,
            margin={"l": 60, "r": 20, "t": 60, "b": 50},
            template="plotly_white",
            legend={"orientation": "h", "y": -0.15 if len(selected_components) == 1 else -0.06},
        )
        return fig, notes

    if selected_components and selected_runs:
        fig, notes = _build()
    else:
        fig = mo.callout(mo.md("Pick at least one component and one run."), kind="info")
        notes = []
    if gain_kind.value != "none":
        notes.insert(
            0,
            "Showing " + processing.gain_label(
                gain_kind.value, gain_factor.value, gain_power.value, gain_start.value
            ) + ".",
        )
    note_md = mo.md("  \n".join(notes)) if notes else mo.md("")
    return fig, note_md


@app.cell
def _(controls, fig, mo, note_md):
    mo.vstack([controls, fig, note_md])


@app.cell(hide_code=True)
def _(h5_reader, mo, target_file):
    mo.accordion({"File metadata": mo.md(h5_reader.format_metadata_text(target_file))})


@app.cell(hide_code=True)
def _(mo):
    mo.md("""
    **Things to try.** The dark line is target minus background: the direct
    wave is the same in both runs, so it cancels and only the cylinder's
    reflection is left. Ex, Ey and Hz are flat because a 2D TMz model never
    updates them. Switch to *Spectrum* to see where the 1.5 GHz Ricker
    source puts its energy.

    Source: [gprMax](https://github.com/gprMax/gprMax), toolbox in
    `gprMax/toolboxes/Marimo/`. Install locally with
    `pip install "gprMax[marimo]"`.
    """)


if __name__ == "__main__":
    app.run()
