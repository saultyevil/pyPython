#!/usr/bin/env python3
"""Base class for Wind objects.

The base class which contains variables containing the parameters of the
wind, as well as the most basic variables which describe the wind.
"""

import pathlib
import re
import warnings

import numpy
from astropy.constants import h, k_B

import pysi
import pysi.util
from pysi.wind import elements, enum


class WindBase:
    """Base wind class for describing a wind object."""

    # Special methods ----------------------------------------------------------

    def __init__(self, root: str, directory: str = pathlib.Path.cwd(), **kwargs) -> None:
        """Initialize the class.

        Parameters
        ----------
        root : str
            The root name of the simulation.
        directory : str
            The directory file path containing the simulation.
        **kwargs : dict
            Various other keywords arguments.

        """
        self.root, self.directory = pysi.util.split_root_and_directory(root, directory)
        self.pf = f"{self.directory}/{root}.pf"
        self.version = kwargs.get("version")
        self.check_version()

        self.n_x = 0
        self.n_z = 0
        self.n_cells = 0
        self.coord_type = enum.CoordSystem.UNKNOWN
        self.x_coords = []
        self.z_coords = []
        self.n_model_freq_bands = 0

        self.parameters = {}
        self.things_read_in = []
        self.ions_read_in = []

        # These units are the default in python. In a higher level class, you
        # should be able to modify the units

        self.distance_units = enum.DistanceUnits.CENTIMETRES
        self.velocity_units = enum.VelocityUnits.CENTIMETRES_PER_SECOND

        # Read in all the variables, spectra, etc.

        self.read_in_wind_parameters()
        self.read_in_wind_ions()
        self.read_in_wind_cell_spectra()
        self.read_in_wind_jnu_models()
        self.things_read_in = self.parameters.keys()
        self._set_axes_coords()

    def __getitem__(self, key: str) -> numpy.ndarray:
        """Get the value of a key.

        Parameters
        ----------
        key : str
            The key to get the value of.

        Returns
        -------
        numpy.ndarray
            The value of the key.

        """
        # if no frac or den is no specified for an ion, default to fractional
        # populations
        if re.match("[A-Z]_i[0-9]+", key):  # matches ion specification, e.g. C_i04  # noqa: SIM102
            if re.match("[A-Z]_i[0-9]+$", key):  # but no type specification at the end, e.g. C_i04_frac
                key += "_frac"  # default to frac if not specified

        return self.parameters[key]

    def __str__(self) -> str:
        """Return a string representation of the Wind object.

        Returns
        -------
        str: A string representation of the Wind object in the format
            "Wind(root=<root> directory=<directory>)".

        """
        return f"Wind(root={self.root!r} directory={str(self.directory)!r})"

    def _set_axes_coords(self) -> None:
        """Set attributes for the x and z axes."""
        self.x_coords = (
            numpy.unique(self.parameters["x"]) if enum.CoordSystem.CYLINDRICAL else numpy.unique(self.parameters["r"])
        )
        if self.n_z > 1:
            self.z_coords = (
                numpy.unique(self.parameters["z"])
                if self.coord_type == enum.CoordSystem.CYLINDRICAL
                else numpy.unique(self.parameters["theta"])
            )
        else:
            self.z_coords = numpy.zeros_like(self.x_coords)

    def check_version(self) -> None:
        """Get the SIROCCO version from file if not already set.

        If the .sirocco-version file cannot be fine, the version is set to
        UNKNOWN.
        """
        if not self.version:
            try:
                with pathlib.Path.open(f"{self.directory}/.sirocco-version") as file_in:
                    self.version = file_in.read()
            except OSError:
                self.version = "UNKNOWN"

    def create_banded_jnu_models(  # noqa: PLR0913
        self,
        cell_index: int,
        band_index: int,
        model_array: numpy.ndarray,
        table_header: list[str],
        n_freq_bins_per_band: int,
        cell_frequency: list[numpy.ndarray],
        cell_flux: list[numpy.ndarray],
    ) -> None:
        """Update the J_nu model for a frequency band.

        Parameters
        ----------
        cell_index: int
            The index of the cell the model is for.
        band_index: int
            The index of the frequency band to model.
        model_array: numpy.ndarray
            An array of values from windsave2table.
        table_header: List[str]
            The header of the winds2table table.
        n_freq_bins_per_band: int
            The number of frequency bins in each frequency band model.
        cell_frequency: List[numpy.ndarray]
            A list to store the frequency bins for the cell.
        cell_flux: List[numpy.ndarry]
            A list to store the fluxes for the cell.

        Returns
        -------
        cell_frequency: List[numpy.ndarray]
            The updated list with frequency bins for the cell.
        cell_flux: List[numpy.ndarry]
            The update list of flux for the cell.

        """
        # create a dict of the parameters for band j, the table is a
        # flat list of the parameters for cell 1, 2, 3, ... for BAND 0,
        # and then the next section is the parameters for cell 1, 2,
        # 3... for BAND 1. So we have to do some funky indexing to get
        # to the correct row element in model_array

        parameters_for_band_j = {
            col: model_array[cell_index + band_index * self.n_cells, k] for k, col in enumerate(table_header)
        }

        band_freq_min = parameters_for_band_j["fmin"]
        band_freq_max = parameters_for_band_j["fmax"]

        # check first that the band hasn't broken in python or if the
        # band is empty as when empty fmin == fmax == 0

        if band_freq_max > band_freq_min:
            band_frequency_bins = numpy.logspace(
                numpy.log10(band_freq_min),
                numpy.log10(band_freq_max),
                n_freq_bins_per_band,
            )

            # model_type 1 == powerlaw model, otherwise 2 == exponential
            # this is the noclumentaure used in python :-)

            model_type = parameters_for_band_j.get("spec_mod_type", parameters_for_band_j.get("spec_mod_"))

            if model_type is None:
                warnings.warn(
                    "The header for the model file is improperly formatted and cannot find 'spec_mode_type'",
                    stacklevel=2,
                )
                return [], []

            with numpy.errstate(over="ignore"):
                if model_type == 1:
                    band_flux = 10 ** (
                        parameters_for_band_j["pl_log_w"]
                        + numpy.log10(band_frequency_bins) * parameters_for_band_j["pl_alpha"]
                    )
                else:
                    band_flux = parameters_for_band_j["exp_w"] * numpy.exp(
                        (-1 * h.cgs.value * band_frequency_bins) / (parameters_for_band_j["exp_temp"] * k_B.cgs.value)
                    )

            cell_frequency.append(band_frequency_bins)
            cell_flux.append(band_flux)

        return cell_frequency, cell_flux

    def get_elem_number_from_ij(self, i: int, j: int) -> int:
        """Get the wind element number for a given i and j index.

        Used when indexing into a 1D array, such as in Python itself.

        Parameters
        ----------
        i: int
            The i-th index of the cell.
        j: int
            The j-th index of the cell.

        """
        return int(self.n_z * i + j)

    def get_ij_from_elem_number(self, elem: int) -> tuple[int, int]:
        """Get the i and j index for a given wind element number.

        Used when converting a wind element number into two indices for use
        in this package.

        Parameters
        ----------
        elem: int
            The element number.

        """
        i = int(elem / self.n_z)
        j = int(elem - i * self.n_z)

        return i, j

    def read_in_wind_table(self, table: str) -> tuple[list[str], numpy.ndarray]:
        """Get variables for a specific table type.

        Parameters
        ----------
        table: str
            The type of table to read in, e.g. master, heat, etc.

        Returns
        -------
        table_header: List[str]
            The table headers for each column.
        table_parameters: numpy.ndarray
            An array of the numerical values of the table.

        """
        file_path = pathlib.Path(f"{self.directory}/{self.root}.{table}.txt")

        if file_path.is_file() is False:
            file_path = pathlib.Path(f"{file_path.parent!s}/tables/{file_path.stem}.txt")
            if file_path.is_file() is False:
                return [], {}

        with pathlib.Path.open(file_path, encoding="utf-8") as buffer:
            file_lines = [line.strip().split() for line in buffer.readlines() if not line.startswith("#")]

        if file_lines[0][0].isdigit() is True:
            msg = "File is formatted incorrectly and missing header"
            raise Exception(msg)

        table_header = file_lines[0]
        table_parameters = numpy.array(file_lines[1:], dtype=numpy.float64)

        return table_header, table_parameters

    def read_in_wind_jnu_models(self, n_freq_bins_per_band: int = 250) -> None:
        """Read in the J_nu models for each cell.

        Parameters
        ----------
        n_freq_bins_per_band: int
            The number of frequency bins to use for the model.

        """
        table_header, models = self.read_in_wind_table("spec")
        if not table_header:
            self.parameters["model_freq"] = self.parameters["model_flux"] = None
            return

        model_array = numpy.array(models, dtype=numpy.float64)

        if model_array.size == 0:
            self.parameters["model_freq"] = self.parameters["model_flux"] = None
            return

        self.n_model_freq_bands = n_bands = int(numpy.max(model_array[:, table_header.index("nband")])) + 1

        if "model_freq" not in self.parameters:
            if self.n_z > 1:
                self.parameters["model_freq"] = numpy.zeros((self.n_x, self.n_z), dtype=list)
            else:
                self.parameters["model_freq"] = numpy.zeros((self.n_x, n_bands), dtype=list)

        if "model_flux" not in self.parameters:
            if self.n_z > 1:
                self.parameters["model_flux"] = numpy.zeros((self.n_x, self.n_z), dtype=list)
            else:
                self.parameters["model_flux"] = numpy.zeros(self.n_x, dtype=list)

        # The next block will loop over each cell and constuct a model for each
        # frequency band, and put that (and the frequency bins) into an array
        # for each cell.

        for cell_index in range(self.n_cells):
            cell_frequency = []
            cell_flux = []

            for band_index in range(n_bands):
                cell_frequency, cell_flux = self.create_banded_jnu_models(
                    cell_index,
                    band_index,
                    model_array,
                    table_header,
                    n_freq_bins_per_band,
                    cell_frequency,
                    cell_flux,
                )

            # If the lists are populated, then join them together as
            # cell_frequency and cell_flux

            if len(cell_flux) != 0:
                i_cell, j_cell = self.get_ij_from_elem_number(cell_index)
                self.parameters["model_freq"][i_cell, j_cell] = numpy.hstack(cell_frequency)
                self.parameters["model_flux"][i_cell, j_cell] = numpy.hstack(cell_flux)

    def read_in_wind_cell_spectra(self) -> None:
        """Read in the cell spectra."""
        spec_table_files = pysi.util.shell.find_file_with_pattern("*xspec.*.txt", self.directory)
        if len(spec_table_files) == 0:
            self.parameters["spec_freq"] = self.parameters["spec_flux"] = None
            return

        for file in spec_table_files:
            with pathlib.Path.open(file, encoding="utf-8") as buffer:
                file_lines = [line.strip().split() for line in buffer.readlines() if not line.startswith("#")]

            if file_lines[0][0].isdigit() is True:
                msg = "File is formatted incorrectly and missing header"
                raise Exception(msg)

            # Get the header and turn the rest of the file into an array, as
            # this makes indexing what we want a lot easier

            file_header = file_lines[0][1:]  # 1: skips the Freq.
            file_array = numpy.array(file_lines[1:], dtype=numpy.float64)

            # Populate the parameters dict

            if "spec_freq" not in self.parameters:
                if self.n_z > 1:
                    self.parameters["spec_freq"] = numpy.zeros((self.n_x, self.n_z, len(file_array[:, 0])))
                else:
                    self.parameters["spec_freq"] = numpy.zeros((self.n_x, len(file_array[:, 0])))

            if "spec_flux" not in self.parameters:
                if self.n_z > 1:
                    self.parameters["spec_flux"] = numpy.zeros((self.n_x, self.n_z, len(file_array[:, 0])))
                else:
                    self.parameters["spec_flux"] = numpy.zeros((self.n_x, len(file_array[:, 0])))

            # Go through each coord string and figure out the coords, and place
            # the spectrum into 1d/2d array

            for i, coord_string in enumerate(file_header):
                coords = numpy.array(coord_string[1:].split("_"), dtype=numpy.int32)
                if self.n_z > 1:
                    self.parameters["spec_flux"][coords[0], coords[1], :] = file_array[:, i + 1]
                    self.parameters["spec_freq"][coords[0], coords[1], :] = file_array[:, 0]
                else:
                    self.parameters["spec_flux"][coords[0], :] = file_array[:, i + 1]
                    self.parameters["spec_freq"][coords[0], :] = file_array[:, 0]

    def read_in_wind_ions(self, elements_to_read: list[str] = elements.ELEMENTS) -> None:
        """Read in the different ions in the wind.

        Parameters
        ----------
        elements_to_read: List[str], optional
            A list of atomic element names, e.g. H, He, whose ions in the wind
            will attempted to be read in. The default value is to try to read in
            all elements up to Cobalt.

        """
        n_read = 0

        # We need to loop over "frac" and "den" because ions are printed in
        # fractional populations or absolute density. The second loop is over
        # the elements passed to the function

        for ion_type in ["frac", "den"]:
            for element in elements_to_read:
                table_header, table_parameters = self.read_in_wind_table(f"{element}.{ion_type}")

                if not table_header:
                    continue

                for i, column in enumerate(table_header):
                    # the re.match here is to ignore any spatial parameters,
                    # e.g. x, z or i and j
                    if re.match("i[0-9]+", column) and column not in self.parameters:
                        ion_name = f"{element}_{column}_{ion_type}"
                        self.parameters[ion_name] = table_parameters[:, i].reshape(self.n_x, self.n_z)
                        self.ions_read_in.append(ion_name)

                n_read += 1

        if n_read == 0:
            raise OSError(f"Have been unable to read in any wind ion tables in {self.directory}")

    def read_in_wind_parameters(self) -> None:
        """Read in the different parameters which describe state of the wind."""
        n_read = 0

        for table in ["master", "heat", "gradient", "converge"]:
            table_header, table_parameters = self.read_in_wind_table(table)

            if not table_header:
                continue

            for i, column in enumerate(table_header):
                if column not in self.parameters:
                    self.parameters[column] = table_parameters[:, i]

            n_read += 1

        if n_read == 0:
            raise OSError(f"Have been unable to read in any wind parameter tables in {self.directory}")

        self.things_read_in = self.parameters.keys()

        # Determine the number of cells in the x and z direction, and the
        # coordinate type of the grid

        self.n_x = int(numpy.max(self.parameters["i"]) + 1)
        if "z" in self.things_read_in or "theta" in self.things_read_in:
            self.n_z = int(numpy.max(self.parameters["j"]) + 1)
        else:
            self.n_z = 1
        self.n_cells = int(self.n_x * self.n_z)

        if "r" in self.parameters and "theta" in self.parameters:
            self.coord_type = enum.CoordSystem.POLAR
        elif "r" in self.parameters:
            self.coord_type = enum.CoordSystem.SPHERICAL
        else:
            self.coord_type = enum.CoordSystem.CYLINDRICAL

        # Reshape the parameters into (nx, nz) which are currently just flat
        # arrays

        self.parameters = {col: val.reshape(self.n_x, self.n_z) for col, val in self.parameters.items()}
