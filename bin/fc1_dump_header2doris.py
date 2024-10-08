#!/usr/bin/env python3

import os
activate_venv_path = os.path.join('/home/yuxiao/.virtualenvs/doris/', 'bin/activate_this.py')
with open(activate_venv_path) as f:
    exec(f.read(), {'__file__': activate_venv_path})

import os
import sys
import h5py
import fnmatch
from typing import Any, Dict
from datetime import datetime, timedelta


SPEED_OF_LIGHT = 299792458


def locate(pattern: str, root=os.curdir) -> str:
    # region docstring
    """Locate the **first** file matching supplied filename pattern
    in and below supplied root directory.

    Parameters
    ----------
    pattern : str
        The pattern that you're looking for. The pattern follows the same rule
        as in linux system, as "*" is allowed.
    root : str, optional
        the root directory for searching the pattern, by default os.curdir.

    Returns
    -------
    str
        the path to the **first** matched file.

    Notes
    -----
    You can use either "return" or "yield", but be aware of the diference
    between the two.
    """
    # endregion

    # TODO: consider using os.getcwd()?
    # see https://stackmirror.com/questions/14512087
    for path, _, files in os.walk(os.path.abspath(root), followlinks=True):
        for filename in fnmatch.filter(files, pattern):
            return os.path.join(path, filename)
    raise FileNotFoundError


def hms2sec(hmsString, convertFlag="int"):
    # convert HMS 2 sec for orbit files.
    # input hmsString syntax: XX:XX:XX.xxxxxx
    secString = (
        int(hmsString[11:13]) * 3600
        + int(hmsString[14:16]) * 60
        + float(hmsString[17:])
    )
    if convertFlag == "int":
        return round(secString)
    if convertFlag == "float":
        return float(secString)
    return round(secString)

def reverse_time(cur_time: datetime):
    current_day = cur_time.replace(microsecond=0, second=0, minute=0, hour=0)
    next_day = current_day + timedelta(days=1)
    time2nextday = next_day - cur_time
    reversed_time = current_day + time2nextday
    return reversed_time

class FC1:
    """FC1 is used to read FC1 meta data and to make it compatible
    with the DORIS (v4) input.

    author: Yuxiao QIN
    date: 2024-Jan
    """

    def __init__(self):
        """[summary]"""
        self.meta = {}  # meta file, empty dictionary

    def locate_meta(self, directory: str):
        """locate the XML file in the directory.

        Parameters
        ----------
        directory : str
            [description]
        """
        pattern = "spacety_SLC_SM*.h5"
        self.meta["path"] = locate(pattern, directory)

        return self

    def read_meta(self):
        """Formatting the meta."""

        query_list: dict = {
            # volume info
            "Volume file": self.meta["path"],
            "Volume_ID": self.meta["path"],
            "Volume_identifier": "product_name",
            "Volume_set_identifier": "acquisition_id",
            # mission info
            "(Check)Number of records in ref. file": "number_of_azimuth_samples",
            "SAR_PROCESSOR": "processor_version",
            "Product type specifier": "satellite_name",
            "Logical volume generating facility": "processor_version",
            "Logical volume creation date": "processing_time",
            "Location and date/time of product creation": "processing_time",
            "Orbit": "orbit_absolute_number",  # Scene identification
            "Direction": "orbit_direction",  # Scene identification
            "Mode": "acquisition_mode",  # Scene identification
            "Leader file": self.meta["path"],
            "Sensor platform mission identifer": "satellite_name",
            # "Scene_centre_latitude": "imageinfo//center//latitude",  # Scene location
            # "Scene_centre_latitude": "imageinfo//center//latitude",  # Scene location
            "Scene_centre": "coord_center",  # Scene location
            # product info
            "Radar_wavelength (m)": "carrier_frequency",
            "First_pixel_azimuth_time (UTC)": "zerodoppler_start_utc",
            "Last_pixel_azimuth_time (UTC)": "zerodoppler_end_utc",
            "Pulse_Repetition_Frequency (computed, Hz)": "processing_prf",
            "Total_azimuth_band_width (Hz)": "total_processed_bandwidth_azimuth",
            "Weighting_azimuth": "window_function_azimuth",
            "DC_Estimate_Coeffs": "dc_estimate_coeffs",
            "Range_time_to_first_pixel (2way) (ms)": "first_pixel_time",
            "Range_sampling_rate (computed, MHz)": "range_sampling_rate",
            "Total_range_band_width (MHz)": "chirp_bandwidth",
            "Weighting_range": "window_function_range",
            # SLC info
            "Datafile": None,
            "Dataformat": None,
            "Number_of_lines_original": "number_of_azimuth_samples",
            "Number_of_pixels_original": "number_of_range_samples",
            # Orbit
            "Orbit Time": "state_vector_time_utc",
            "Orbit X": "posX",
            "Orbit Y": "posY",
            "Orbit Z": "posZ",
            # Look Side
            "Look Side": "look_side",
        }

        # get variables and parameters from xml
        container: Dict[str, Any] = {}

        with h5py.File(self.meta["path"], 'r') as f:

            for key, value in query_list.items():
                if value is None:
                    container[key] = "unknown"
                elif value.endswith(".h5"):  # metafile
                    container[key] = os.path.basename(value)
                else:
                    tmp_val = f[value][()]
                    # remember to convert bytes to str if needed
                    container[key] = tmp_val.decode() if isinstance(tmp_val, bytes) else tmp_val

        # entries that have to be manually updated
        container["Scene_centre_latitude"] = container["Scene_centre"][2]
        container["Scene_centre_longitude"]= container["Scene_centre"][3]

        container["Orbit_n_pts"] = len(container["Orbit Time"])
        container["Scene identification"] = (
            "Orbit: "
            + str(container["Orbit"])  # this doesn't mean anything at this moment.
            + " "
            + str(container["Direction"])
            + " Mode: "
            + str(container["Mode"])
        )
        container["Scene location"] = (
            "lat: "
            + str(container["Scene_centre_latitude"])
            + " lon: "
            + str(container["Scene_centre_longitude"])
        )
        container["Datafile"] = os.path.basename(
            locate("spacety_SLC_SM*.h5", os.path.dirname(self.meta["path"]))
        )

        # correct two way slant range time
        container["Range_time_to_first_pixel (2way) (ms)"] = (
            1000 * float(container["Range_time_to_first_pixel (2way) (ms)"])
        )

        container["Range_sampling_rate (computed, MHz)"] = container["Range_sampling_rate (computed, MHz)"] / 1e6
        container["Total_range_band_width (MHz)"] = container["Total_range_band_width (MHz)"] / 1e6

        container["Radar_wavelength (m)"] = SPEED_OF_LIGHT / container["Radar_wavelength (m)"]

        # Doppler
        container["Xtrack_f_DC_constant (Hz, early edge)"] = container["DC_Estimate_Coeffs"][0][0]
        container["Xtrack_f_DC_linear (Hz/s, early edge)"] = container["DC_Estimate_Coeffs"][0][1]
        container["Xtrack_f_DC_quadratic (Hz/s/s, early edge)"]= container["DC_Estimate_Coeffs"][0][2]

        # update the time format
        cur_time = datetime.strptime(container["First_pixel_azimuth_time (UTC)"], "%Y-%m-%dT%H:%M:%S.%f")
        if container["Look Side"] == "left":
            cur_time = reverse_time(cur_time)  # reverse time to "fake" right looking
        container["First_pixel_azimuth_time (UTC)"] = (
            datetime.strftime(cur_time, "%d-%b-%Y %H:%M:%S.%f")
        )

        container["Dataformat"] = "HDF5"
        container["Product type specifier"] = "FC1"
        container["Sensor platform mission identifer"] = "FC1"

        self.meta.update(container)

        return self

    def export2res(self) -> None:
        """EXPORT2RES exports the meta into .res format that's compatible with doris."""
        keys_lead = (
            "Volume file",
            "Volume_ID",
            "Volume_set_identifier",
            "(Check)Number of records in ref. file",
            "SAR_PROCESSOR",
            "Product type specifier",
            "Logical volume generating facility",
            "Logical volume creation date",
            "Location and date/time of product creation",
            "Scene identification",
            "Scene location",
            "Leader file",
            "Sensor platform mission identifer",
            "Scene_centre_latitude",
            "Scene_centre_longitude",
            "Radar_wavelength (m)",
            "First_pixel_azimuth_time (UTC)",
            "Pulse_Repetition_Frequency (computed, Hz)",
            "Total_azimuth_band_width (Hz)",
            "Weighting_azimuth",
            "Xtrack_f_DC_constant (Hz, early edge)",
            "Xtrack_f_DC_linear (Hz/s, early edge)",
            "Xtrack_f_DC_quadratic (Hz/s/s, early edge)",
            "Range_time_to_first_pixel (2way) (ms)",
            "Range_sampling_rate (computed, MHz)",
            "Total_range_band_width (MHz)",
            "Weighting_range",
        )

        keys_file = (
            "Datafile",
            "Dataformat",
            "Number_of_lines_original",
            "Number_of_pixels_original",
        )

        print("\nfc1_dump_header2doris.py v1,0, doris software, 2021\n")
        print("**************************************************************")
        print("*_Start_readfiles:")
        print("**************************************************************")

        for keys in keys_lead:
            print("{:<50}\t{}".format(keys + ":", self.meta[keys]))

        print("")
        print("**************************************************************")
        for keys in keys_file:
            print("{:<50}\t{}".format(keys + ":", self.meta[keys]))

        print("**************************************************************")
        print("* End_readfiles:_NORMAL")
        print("**************************************************************")
        print("")
        print("")
        print("**************************************************************")
        print("*_Start_leader_datapoints")
        print("**************************************************************")
        print(" t(s)		X(m)		Y(m)		Z(m)")
        print("NUMBER_OF_DATAPOINTS: 			{}".format(self.meta["Orbit_n_pts"]))  # nopep8
        print("")

        if self.meta["Look Side"] == "left":  # fake right looking
            for i in reversed(range(0, self.meta["Orbit_n_pts"])):

                x, y, z = [
                    e
                    for e in (
                        self.meta["Orbit X"][i],
                        self.meta["Orbit Y"][i],
                        self.meta["Orbit Z"][i],
                    )
                ]  # format in a nicer way

                cur_orb_time = self.meta["Orbit Time"][i][0].decode()
                cur_orb_time = reverse_time(datetime.strptime(cur_orb_time, "%Y-%m-%dT%H:%M:%S.%f"))
                cur_orb_time = datetime.strftime(cur_orb_time, "%Y-%m-%dT%H:%M:%S.%f")
                print(
                    " {:>7} {:>15} {:>15} {:>15}".format(
                        hms2sec(cur_orb_time, convertFlag="float"),
                        x,
                        y,
                        z
                    )
                )
        else:
            for i in range(0, self.meta["Orbit_n_pts"]):

                x, y, z = [
                    e
                    for e in (
                        self.meta["Orbit X"][i],
                        self.meta["Orbit Y"][i],
                        self.meta["Orbit Z"][i],
                    )
                ]  # format in a nicer way

                cur_orb_time = self.meta["Orbit Time"][i][0].decode()
                print(
                    " {:>7} {:>15} {:>15} {:>15}".format(
                        hms2sec(cur_orb_time, convertFlag="float"),
                        x,
                        y,
                        z
                    )
                )

        print("\n")
        print("**************************************************************")
        print("* End_leader_datapoints:_NORMAL")
        print("**************************************************************")

    @staticmethod
    def usage() -> None:
        """A quick guide of how to call the script."""
        print("INFO    : @(#)FC1 for Doris, Author: Yuxiao")
        print("\n")
        print("Usage   : python fc1_dump_header2doris.py metafile")  # nopep8
        print("          - `metafile` is the FC1 meta file in xml format.")
        print("\n")
        print("This software is part of Doris InSAR software package.\n")


if __name__ == "__main__":
    fc1 = FC1()

    # figure out the input parameters.
    if len(sys.argv) != 2:
        print("\nError   : Unrecognized input or missing arguments!\n\n")
        fc1.usage()
        sys.exit(1)
    try:
        meta_file = sys.argv[1]
    except IndexError:
        print("\nError   : Unrecognized input or missing arguments!\n\n")
        fc1.usage()
        sys.exit(1)

    fc1.meta["path"] = meta_file
    fc1.read_meta().export2res()
    # fc1.read_meta()
