# Copyright (C) 2015-2026: The University of Edinburgh, United Kingdom
#
# This file is part of the gprMax source code base.
#
# gprMax is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# gprMax is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with gprMax. If not, see <https://www.gnu.org/licenses/>.

"""fft_power copied unchanged from gprMax/utilities/utilities.py (gprMax v.4.0.2).

The rest of that module is not needed by the browser demo.
"""

import numpy as np


def fft_power(waveform, dt):
    """Calculates FFT of the given waveform of amplitude values;
        converted to decibels and shifted so that maximum power is 0dB

    Args:
        waveform: array containing time domain waveform.
        dt: float of time step.

    Returns:
        freq: array of frequency bins.
        power: array containing power spectra.
    """

    waveform = np.asarray(waveform)
    if waveform.ndim != 1 or waveform.size == 0:
        raise ValueError("waveform must be a non-empty one-dimensional array")
    if not np.isfinite(dt) or dt <= 0:
        raise ValueError("dt must be finite and greater than zero")

    magnitude = np.abs(np.fft.fft(waveform))
    maximum = np.max(magnitude)
    if maximum == 0:
        power = np.full(magnitude.shape, -np.inf, dtype=float)
    else:
        # Normalise before taking the logarithm. Spectral nulls intentionally
        # remain -inf rather than being turned into apparent 0 dB peaks.
        with np.errstate(divide="ignore", invalid="ignore"):
            power = 20 * np.log10(magnitude / maximum)

    # Frequency bins
    freqs = np.fft.fftfreq(power.size, d=dt)

    return freqs, power
