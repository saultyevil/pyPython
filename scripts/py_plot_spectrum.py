#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Create plots of the spectrum files from a Python simulation.

This script will create,
"""

import argparse as ap

from matplotlib import pyplot as plt

from pypython import Spectrum, plot


def setup_script():
    """Parse the different modes this script can be run from the command line.

    Returns
    -------
    setup: tuple
        A list containing all of the different setup of parameters for
        plotting.
    """

    p = ap.ArgumentParser(description=__doc__)

    p.add_argument("root", help="The root name of the simulation.")
    p.add_argument("-fp", "--filepath", default=".", help="The directory containing the simulation.")
    p.add_argument("-xl", "--xmin", type=float, default=None, help="The lower x-axis boundary to display.")
    p.add_argument("-xu", "--xmax", type=float, default=None, help="The upper x-axis boundary to display.")
    p.add_argument("-s",
                   "--scales",
                   default="logy",
                   choices=["logx", "logy", "loglog", "linlin"],
                   help="The axes scaling to use: logx, logy, loglog, linlin.")
    p.add_argument("-l",
                   "--label_lines",
                   action="store_true",
                   default=False,
                   help="Plot labels for important absorption edges.")
    p.add_argument("-f",
                   "--flux",
                   action="store_true",
                   default=False,
                   help="Create the figure in frequency space.")
    p.add_argument("-sm", "--smooth_amount", type=int, default=5, help="The size of the boxcar smoothing filter.")
    p.add_argument("--display", action="store_true", default=False, help="Display the plot before exiting the script.")

    args = p.parse_args()

    return (args.root, args.filepath, args.xmin, args.xmax, args.flux, args.label_lines, args.scales,
            args.smooth_amount, args.display)


def main():
    """The main function of the script. First, the important wind quantaties
    are plotted. This is then followed by the important ions.

    Returns
    -------
    fig: plt.Figure
        The matplotlib Figure object for the created plot.
    ax: plt.Axes
        The matplotlib Axes objects for the plot panels.
    """

    root, fp, xmin, xmax, flux, label_lines, scales, smooth, display = setup_script()

    spectrum = Spectrum(root, fp, smooth=smooth)

    # Observer spectra

    try:
        spectrum.set("spec")
        plot.spectrum.spectrum_observer(spectrum, "all", xmin, xmax, scales, flux, label_lines, display)
        plot.spectrum.spectrum_components(spectrum, xmin, xmax, scales, use_flux=flux, display=display)
    except IndexError:
        print(f"Unable to plot observer spectra as no {fp}/{root}.spec file exists")

    # spec_tot - all photons

    try:
        spectrum.set("spec_tot")
        plot.spectrum.spectrum_components(spectrum, xmin, xmax, scales, use_flux=flux, display=display)
    except IndexError:
        print(f"Unable to plot ionization spectra as no {fp}/{root}.spec_tot file exists")

    # spec_tot_wind - anything which is "inwind"

    try:
        spectrum.set("spec_tot_wind")
        plot.spectrum.spectrum_components(spectrum, xmin, xmax, scales, use_flux=flux, display=display)
    except IndexError:
        print(f"Unable to plot ionization spectra of wind photons as no {fp}/{root}.spec_tot_wind file exists")

    if display:
        plt.show()
    else:
        plt.close()


if __name__ == "__main__":
    main()
