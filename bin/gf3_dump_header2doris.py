from _typeshed import NoneType
import os
import fnmatch
import xml.etree.ElementTree as ET


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

    def read_meta(self):
        """[summary]"""

        # query syntax for every field
        queryList = {
            # volume info
            "Volume file": self.meta["path"],
            "Volume_ID": "productinfo//productType",
            "Volume_identifier": "DocumentIdentifier",
            "Volume_set_identifier": None,
            # mission info
            "(Check)Number of records in ref. file": "imageAttributes//numberOfLines",
            "SAR_PROCESSOR": "Station",
            "Product type specifier": "sourceAttributes/satellite",
            "Logical volume generating facility": "Station",
            "Logical volume creation date": "productinfo//productGentime",
            "Location and date/time of product creation": "productinfo//productGentime",
            "Orbit": "orbitID",  # Scene identification
            "Direction": "Direction",  # Scene identification
            "Mode": "sensor//imagingMode",  # Scene identification
            "Leader file": self.meta["path"],
            "Sensor platform mission identifer": "sourceAttributes/satellite",
            "Scene_centre_latitude": "imageinfo//center//latitude",  # Scene location
            "Scene_centre_longitude": "imageinfo//center//longitude",  # Scene location
            # product info
            "Radar_wavelength (m)": "sensor//lamda",
            "First_pixel_azimuth_time (UTC)": "imageinfo//imagingTime//start",
            "Pulse_Repetition_Frequency (computed, Hz)": "imageinfo//eqvPRF",
            "Total_azimuth_band_width (Hz)": "processinfo//TotalProcessedAzimuthBandWidth",
            "Weighting_azimuth": "processinfo//AzimuthWeightType",
            "Xtrack_f_DC_constant (Hz, early edge)": "processinfo//DopplerCentroidCoefficients//d0",
            "Xtrack_f_DC_linear (Hz/s, early edge)": "processinfo//DopplerCentroidCoefficients//d1",
            "Xtrack_f_DC_quadratic (Hz/s/s, early edge)": "processinfo//DopplerCentroidCoefficients//d2",
            "Range_time_to_first_pixel (2way) (ms)": "imageinfo//nearRange",
            "Range_sampling_rate (computed, MHz)": "imageinfo//eqvPRF",
            "Total_range_band_width (MHz)": "processinfo//RangeLookBandWidth",
            "Weighting_range": "processinfo//RangeWeightType"
        }

        inTree = ET.parse(self.meta["path"])

        # get variables and parameters from xml
        container = {}
        for key, value in queryList.iteritems():  # ignore:type
            if key.startswith("list_"):
                container[key] = [
                    tag.text for tag in inTree.findall(nsmap_none(value, ns))
                ]
            else:
                container[key] = inTree.findtext(nsmap_none(value, ns))
                if container[key] == None:
                    raise Exception("Path {0} not found in XML".format(value))

        container["dopplerCoeff"] = container["dopplerCoeff"].split()

        pass

    def export2res(self) -> None:
        """[summary]"""
        pass

    def usage(self) -> None:
        """[summary]"""
        pass


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


if __name__ == "__main__":
    pass
