#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
The purpose of this script is to tie together a bunch of plotting scripts into
one script. This way, instead of running each plotting script, one only needs
to run this script. However, the plots will be created with a default set of
parameters to keep this script simple. If you want more flexible options,
use (or edit) the other plotting scripts to fit your needs appropriately.
"""

import argparse as ap
import os

import pypython

import py_plot_optical_depth
import py_plot_spectrum
import py_plot_wind


def setup_script() -> tuple:
    """Parse the different modes this script can be run from the command line.

    Returns
    -------
    setup: tuple
        A list containing all of the different setup of parameters for plotting.

        setup = (
            root,
            wd,
            xmin,
            xmax,
            frequency_space,
            projection,
            smooth_amount,
            file_ext,
            display
        )"""

    p = ap.ArgumentParser(description=__doc__)

    p.add_argument(
        "root", type=str, help="The root name of the simulation."
    )
    p.add_argument(
        "-wd", "--working_directory", default=".", help="The directory containing the simulation."
    )
    p.add_argument(
        "-xl", "--xmin", type=float, default=None, help="The lower x-axis boundary to display."
    )
    p.add_argument(
        "-xu", "--xmax", type=float, default=None, help="The upper x-axis boundary to display."
    )
    p.add_argument(
        "-f", "--frequency_space", action="store_true", default=False, help="Create the figure in frequency space."
    )
    p.add_argument(
        "-p", "--polar", action="store_true", default=False, help="Plot using polar projection."
    )
    p.add_argument(
        "-sm", "--smooth_amount", type=int, default=5, help="The size of the boxcar smoothing filter."
    )
    p.add_argument(
        "-e", "--ext", default="png", help="The file extension for the output figure."
    )
    p.add_argument(
        "--display", action="store_true", default=False, help="Display the plot before exiting the script."
    )

    args = p.parse_args()

    setup = (
        args.root,
        args.working_directory,
        args.xmin,
        args.xmax,
        args.frequency_space,
        args.polar,
        args.smooth_amount,
        args.ext,
        args.display
    )

    return setup


def plot(
    setup: tuple = None
):
    """Creates a bunch of plots using some parameters which can be controlled at
    run time, but also assumes a few default parameters. Refer to the
    documentation for the script for more detail.

    This function basically just runs the main() functions from a bunch of the
    other plotting scripts located in the same directory.

    Parameters
    ----------
    setup: tuple
        A tuple containing the setup parameters to run the script. If this
        isn't provided, then the script will parse them from the command line.

    Returns
    -------
    fig: plt.Figure
        The matplotlib Figure object for the created plot.
    ax: plt.Axes
        The matplotlib Axes objects for the plot panels."""

    if setup:
        root, wd, xmin, xmax, frequency_space, polar_coords, smooth_amount, file_ext, display = setup
    else:
        root, wd, xmin, xmax, frequency_space, polar_coords, smooth_amount, file_ext, display = setup_script()

    # todo: why did I write this? i am very confused :-(
    # Oh it's because projection was a string, I think, but I should still change
    # this garbage bit of code

    # if polar_coords:
    #     polar_coords = True
    # else:
    #     polar_coords = False

    if not os.path.isfile("{}.master.txt".format(root)):
        pypython.util.create_wind_save_tables(root, wd, False)
        pypython.util.create_wind_save_tables(root, wd, True)

    # Create plots for the wind - only create velocity plots for rectilinear
    # at the moment - and remove the data folder afterwards

    try:
        py_plot_wind.main(
            (root, wd, polar_coords, False, "loglog", False, file_ext, display)
        )
    except Exception as e:
        print("Problem when plotting model wind")
        print(e)

    # Create plots for the different spectra
    try:
        py_plot_spectrum.main(
            (root, wd, xmin, xmax, frequency_space, True, "logy", smooth_amount, file_ext, display)
        )
    except Exception as e:
        print("Problem when plotting model spectra")
        print(e)

    try:
        py_plot_optical_depth.main(
            (root, wd, xmin, xmax, False, True, "loglog", file_ext, display)
        )
    except Exception as e:
        print("Problem with plotting optical depth spectrum")
        print(e)

    return


if __name__ == "__main__":
    plot()
