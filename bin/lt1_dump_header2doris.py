#!/usr/bin/env python3

import os
activate_venv_path = os.path.join('/home/yuxiao/.virtualenvs/doris/', 'bin/activate_this.py')
with open(activate_venv_path) as f:
    exec(f.read(), {'__file__': activate_venv_path})

import os
import sys
import fnmatch
from typing import Any, Dict
from xml.etree import ElementTree
from datetime import datetime


SPEED_OF_LIGHT = 299792458


def locate(pattern: str, root=os.curdir) -> str:
    """Locate the first file matching pattern in directory tree"""
    for path, dirs, files in os.walk(os.path.abspath(root), followlinks=True):
        for filename in fnmatch.filter(files, pattern):
            return os.path.join(path, filename)
    raise FileNotFoundError


def hms2sec(timestr: str, convertFlag: str = "int") -> float:
    """Convert time string to seconds"""
    time_parts = timestr.split('T')[1].split(':')
    secString = (
        int(time_parts[0]) * 3600
        + int(time_parts[1]) * 60
        + float(time_parts[2])
    )
    if convertFlag == "int":
        return round(secString)
    elif convertFlag == "float":
        return float(secString)
    else:
        return round(secString)


class LT1:
    """LT1 is used to read LuTan-1 (LT1) meta data and to make it compatible
    with the DORIS (v4) input.

    author: Yuxiao QIN
    date: 2025-Jan
    """

    def __init__(self):
        """Initialize empty metadata dictionary"""
        self.meta = {}

    def locate_meta(self, directory: str):
        """Locate metadata file in directory"""
        pattern = "LT1*SLC*.meta.xml"
        self.meta["path"] = locate(pattern, directory)
        return self

    def read_meta(self):
        """Read and format metadata from XML file"""
        query_list = {
            # volume info
            "Volume file": self.meta["path"],
            "Volume_ID": "generalHeader//itemName",
            "Volume_identifier": "productInfo//generationInfo//logicalProductID",
            "Volume_set_identifier": None,
            # mission info
            "(Check)Number of records in ref. file": "productInfo//imageDataInfo//imageRaster//numberOfRows",
            "SAR_PROCESSOR": "generalHeader//generationSystem",
            "Product type specifier": "generalHeader//mission",
            "Logical volume generating facility": "productInfo//generationInfo//level1ProcessingFacility",
            "Logical volume creation date": "generalHeader//generationTime",
            "Location and date/time of product creation": "generalHeader//generationTime",
            "Orbit": "productInfo//missionInfo//absOrbit",
            "Direction": "productInfo//missionInfo//orbitDirection",
            "Mode": "productInfo//acquisitionInfo//imagingMode",
            "Leader file": self.meta["path"],
            "Sensor platform mission identifer": "generalHeader//mission",
            "Scene_centre_latitude": "productInfo//sceneInfo//sceneCenterCoord//lat",
            "Scene_centre_longitude": "productInfo//sceneInfo//sceneCenterCoord//lon",
            # product info
            "Radar_wavelength (m)": None,  # Will calculate from centerFrequency
            "First_pixel_azimuth_time (UTC)": "productInfo//sceneInfo//start//timeUTC",
            "Last_pixel_azimuth_time (UTC)": "productInfo//sceneInfo//stop//timeUTC",
            "Pulse_Repetition_Frequency (computed, Hz)": "instrument//settings//settingRecord//PRF",
            "Total_azimuth_band_width (Hz)": "processing//processingParameter//totalProcessedAzimuthBandwidth",
            "Weighting_azimuth": "processing//processingParameter//azimuthWindowID",
            "Xtrack_f_DC_constant (Hz, early edge)": None,
            "Xtrack_f_DC_linear (Hz/s, early edge)": None,
            "Xtrack_f_DC_quadratic (Hz/s/s, early edge)": None,
            "Range_time_to_first_pixel (2way) (ms)": "productInfo//sceneInfo//rangeTime//firstPixel",
            "Range_sampling_rate (computed, MHz)": "instrument//settings//RSF",
            "Total_range_band_width (MHz)": "processing//processingParameter//totalProcessedRangeBandwidth",
            "Weighting_range": "processing//processingParameter//rangeWindowID",
            # SLC info
            "Datafile": None,
            "Dataformat": "productInfo//imageDataInfo//imageDataFormat",
            "Number_of_lines_original": "productInfo//imageDataInfo//imageRaster//numberOfRows",
            "Number_of_pixels_original": "productInfo//imageDataInfo//imageRaster//numberOfColumns",
            # Orbit data
            "Orbit Time": "platform//orbit//stateVec//timeUTC",
            "Orbit X": "platform//orbit//stateVec//posX",
            "Orbit Y": "platform//orbit//stateVec//posY",
            "Orbit Z": "platform//orbit//stateVec//posZ",
        }

        # Initialize containers for orbit data
        container: Dict[str, Any] = {
            "Orbit Time": [],
            "Orbit X": [],
            "Orbit Y": [],
            "Orbit Z": [],
        }

        # Parse XML
        root = ElementTree.parse(self.meta["path"]).getroot()

        # Get values from XML
        for key, value in query_list.items():
            if value is None:
                container[key] = "Unknown"
            elif value.endswith(".xml"):
                container[key] = os.path.basename(value)
            else:
                for item in root.findall(value):
                    if key.startswith("Orbit "):
                        container[key].append(item.text)
                    else:
                        container[key] = item.text

        # Calculate radar wavelength
        center_freq = float(root.find("instrument//radarParameters//centerFrequency").text)
        container["Radar_wavelength (m)"] = str(SPEED_OF_LIGHT / center_freq)

        # Convert bandwidth values from Hz to MHz
        for key in ["Range_sampling_rate (computed, MHz)", "Total_range_band_width (MHz)"]:
            if key in container and container[key] is not None:
                try:
                    value_hz = float(container[key])
                    container[key] = str(value_hz / 1e6)
                except (ValueError, TypeError):
                    print(f"Warning: Could not convert {key} to MHz")
                    container[key] = "Unknown"

        # Get Doppler coefficients
        doppler_coeffs = root.findall("processing//doppler//dopplerCentroid//dopplerEstimate//combinedDoppler//coefficient")
        if doppler_coeffs:
            container["Xtrack_f_DC_constant (Hz, early edge)"] = doppler_coeffs[0].text
            container["Xtrack_f_DC_linear (Hz/s, early edge)"] = doppler_coeffs[1].text if len(doppler_coeffs) > 1 else "0"
            container["Xtrack_f_DC_quadratic (Hz/s/s, early edge)"] = doppler_coeffs[2].text if len(doppler_coeffs) > 2 else "0"

        # Manual updates
        container["Orbit_n_pts"] = len(container["Orbit Time"])
        container["Volume_set_identifier"] = "DUMMY"
        container["Scene identification"] = (
            f"Orbit: {container['Orbit']} {container['Direction']} Mode: {container['Mode']}"
        )
        container["Scene location"] = (
            f"lat: {container['Scene_centre_latitude']} lon: {container['Scene_centre_longitude']}"
        )
        container["Datafile"] = os.path.basename(
            locate("LT1*SLC*.tiff", os.path.dirname(self.meta["path"]))
        )

        # Convert range time to ms
        container["Range_time_to_first_pixel (2way) (ms)"] = str(float(container["Range_time_to_first_pixel (2way) (ms)"]) * 1000)

        # Update time format
        container["First_pixel_azimuth_time (UTC)"] = (
            datetime.strptime(
                container["First_pixel_azimuth_time (UTC)"],
                "%Y-%m-%dT%H:%M:%S.%f"
            ).strftime("%d-%b-%Y %H:%M:%S.%f")
        )

        self.meta.update(container)
        return self

    def export2res(self) -> None:
        """Export metadata in DORIS-compatible format"""
        keys_lead = (
            "Volume file", "Volume_ID", "Volume_set_identifier",
            "(Check)Number of records in ref. file", "SAR_PROCESSOR",
            "Product type specifier", "Logical volume generating facility",
            "Logical volume creation date", "Location and date/time of product creation",
            "Scene identification", "Scene location", "Leader file",
            "Sensor platform mission identifer", "Scene_centre_latitude",
            "Scene_centre_longitude", "Radar_wavelength (m)",
            "First_pixel_azimuth_time (UTC)", "Pulse_Repetition_Frequency (computed, Hz)",
            "Total_azimuth_band_width (Hz)", "Weighting_azimuth",
            "Xtrack_f_DC_constant (Hz, early edge)", "Xtrack_f_DC_linear (Hz/s, early edge)",
            "Xtrack_f_DC_quadratic (Hz/s/s, early edge)",
            "Range_time_to_first_pixel (2way) (ms)", "Range_sampling_rate (computed, MHz)",
            "Total_range_band_width (MHz)", "Weighting_range"
        )

        keys_file = (
            "Datafile", "Dataformat", "Number_of_lines_original",
            "Number_of_pixels_original"
        )

        print("\nlt1_dump_header2doris.py v1.0, doris software, 2024\n")
        print("**************************************************************")
        print("*_Start_readfiles:")
        print("**************************************************************")

        for keys in keys_lead:
            print("{:<50}\t{}".format(keys + ":", self.meta[keys]))

        print("\n**************************************************************")
        for keys in keys_file:
            print("{:<50}\t{}".format(keys + ":", self.meta[keys]))

        print("**************************************************************")
        print("* End_readfiles:_NORMAL")
        print("**************************************************************\n\n")
        print("**************************************************************")
        print("*_Start_leader_datapoints")
        print("**************************************************************")
        print(" t(s)		X(m)		Y(m)		Z(m)")
        print(f"NUMBER_OF_DATAPOINTS: 			{self.meta['Orbit_n_pts']}\n")

        for i in range(self.meta["Orbit_n_pts"]):
            x, y, z = [self.meta[f"Orbit {coord}"][i] for coord in "XYZ"]
            print(f" {hms2sec(self.meta['Orbit Time'][i]):>7} {x:>15} {y:>15} {z:>15}")

        print("\n**************************************************************")
        print("* End_leader_datapoints:_NORMAL")
        print("**************************************************************")

    @staticmethod
    def usage() -> None:
        """Print usage information"""
        print("INFO    : @(#)LuTan-1 for Doris, Author: Yuxiao")
        print("\nUsage   : python lt1_dump_header2doris.py metafile")
        print("          - `metafile` is the LT1 meta file in xml format.\n")
        print("This software is part of Doris InSAR software package.\n")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("\nError   : Unrecognized input or missing arguments!\n")
        LT1.usage()
        sys.exit(1)

    meta_file = sys.argv[1]
    lt1 = LT1()
    lt1.meta["path"] = meta_file
    lt1.read_meta().export2res()
