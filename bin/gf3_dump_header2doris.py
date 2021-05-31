#!/usr/bin/env python3


import os
import sys
import fnmatch
from typing import Any, Dict
from xml.etree import ElementTree


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
    for path, dirs, files in os.walk(os.path.abspath(root), followlinks=True):
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
    elif convertFlag == "float":
        return float(secString)
    else:
        return round(secString)


class GF3:
    """GF3 is used to read GaoFen-3 (GF3) meta data and to make it compatible
    with the DORIS (v4) input.

    author: Yuxiao QIN
    date: 2021-Mar
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
        pattern = "GF3*L1A*.meta.xml"
        self.meta["path"] = locate(pattern, directory)

        return self

    def read_meta(self):
        """Formatting the meta."""

        query_list: dict = {
            # volume info
            "Volume file": self.meta["path"],
            "Volume_ID": "productinfo//productType",
            "Volume_identifier": "productID",
            "Volume_set_identifier": None,
            # mission info
            "(Check)Number of records in ref. file": "imageinfo//height",
            "SAR_PROCESSOR": "Station",
            "Product type specifier": "satellite",
            "Logical volume generating facility": "Station",
            "Logical volume creation date": "productinfo//productGentime",
            "Location and date/time of product creation": "productinfo//productGentime",
            "Orbit": "orbitID",  # Scene identification
            "Direction": "Direction",  # Scene identification
            "Mode": "sensor//imagingMode",  # Scene identification
            "Leader file": self.meta["path"],
            "Sensor platform mission identifer": "satellite",
            "Scene_centre_latitude": "imageinfo//center//latitude",  # Scene location
            "Scene_centre_longitude": "imageinfo//center//longitude",  # Scene location
            # product info
            "Radar_wavelength (m)": "sensor//lamda",
            "First_pixel_azimuth_time (UTC)": "imageinfo//imagingTime//start",
            "Pulse_Repetition_Frequency (computed, Hz)": "imageinfo//eqvPRF",
            "Total_azimuth_band_width (Hz)": "processinfo//TotalProcessedAzimuthBandWidth",
            "Weighting_azimuth": None,
            "Xtrack_f_DC_constant (Hz, early edge)": "processinfo//DopplerCentroidCoefficients//d0",
            "Xtrack_f_DC_linear (Hz/s, early edge)": "processinfo//DopplerCentroidCoefficients//d1",
            "Xtrack_f_DC_quadratic (Hz/s/s, early edge)": "processinfo//DopplerCentroidCoefficients//d2",
            "Range_time_to_first_pixel (2way) (ms)": "imageinfo//nearRange",
            "Range_sampling_rate (computed, MHz)": "imageinfo//eqvFs",
            "Total_range_band_width (MHz)": "processinfo//RangeLookBandWidth",
            "Weighting_range": None,
            # SLC info
            "Datafile": None,
            "Dataformat": "productinfo//productFormat",
            "Number_of_lines_original": "imageinfo//height",
            "Number_of_pixels_original": "imageinfo//width",
            # Orbit
            "Orbit Time": "GPS//GPSParam//TimeStamp",
            "Orbit X": "GPS//GPSParam//xPosition",
            "Orbit Y": "GPS//GPSParam//yPosition",
            "Orbit Z": "GPS//GPSParam//zPosition",
        }

        # get variables and parameters from xml
        container: Dict[str, Any] = {
            "Orbit Time": [],
            "Orbit X": [],
            "Orbit Y": [],
            "Orbit Z": [],
        }
        root = ElementTree.parse(self.meta["path"]).getroot()
        for key, value in query_list.items():
            if value is None:
                container[key] = "Unknown"
            elif value.endswith(".xml"):  # metafile
                container[key] = os.path.basename(value)
            else:
                for item in root.findall(value):
                    # for item in root.findall(value):
                    if key.startswith("Orbit "):  # space is necessary here.
                        container[key].append(item.text)
                    else:
                        container[key] = item.text

        # Two entries that have to be manually updated
        container["Orbit_n_pts"] = len(container["Orbit Time"])
        container["Volume_set_identifier"] = "DUMMY"
        container["Scene identification"] = (
            "Orbit: "
            + container["Orbit"]
            + " "
            + container["Direction"]
            + " Mode: "
            + container["Mode"]
        )
        container["Scene location"] = (
            "lat: "
            + container["Scene_centre_latitude"]
            + " lon: "
            + container["Scene_centre_longitude"]
        )
        container["Datafile"] = os.path.basename(
            locate("GF3*L1A*.tiff", os.path.dirname(self.meta["path"]))
        )

        # correct two way slant range time
        container["Range_time_to_first_pixel (2way) (ms)"] = (  # us to ms
            float(container["Range_time_to_first_pixel (2way) (ms)"]) * 10 ** -6
        )

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

        print("\ngf3_dump_header2doris.py v1,0, doris software, 2021\n")
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

        for i in range(0, self.meta["Orbit_n_pts"]):

            x, y, z = [
                e
                for e in (
                    self.meta["Orbit X"][i],
                    self.meta["Orbit Y"][i],
                    self.meta["Orbit Z"][i],
                )
            ]  # format in a nicer way

            print(
                " {:>7} {:>15} {:>15} {:>15}".format(
                    hms2sec(self.meta["Orbit Time"][i]), x, y, z
                )
            )

        print("\n")
        print("**************************************************************")
        print("* End_leader_datapoints:_NORMAL")
        print("**************************************************************")

    @staticmethod
    def usage() -> None:
        """A quick guide of how to call the script."""
        print("INFO    : @(#)GaoFen3 for Doris, Author: Yuxiao")
        print("\n")
        print("Usage   : python gf3_dump_header2doris.py metafile")  # nopep8
        print("          - `metafile` is the GF3 meta file in xml format.")
        print("\n")
        print("This software is part of Doris InSAR software package.\n")


if __name__ == "__main__":
    gf3 = GF3()

    # figure out the input parameters.
    if len(sys.argv) != 2:
        print("\nError   : Unrecognized input or missing arguments!\n\n")
        gf3.usage()
        sys.exit(1)
    try:
        meta_file = sys.argv[1]
    except Exception:
        print("\nError   : Unrecognized input or missing arguments!\n\n")
        gf3.usage()
        sys.exit(1)

    gf3.meta["path"] = meta_file
    gf3.read_meta().export2res()
