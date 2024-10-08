#!/usr/bin/env python3

import os
activate_venv_path = os.path.join('/home/yuxiao/.virtualenvs/doris/', 'bin/activate_this.py')
with open(activate_venv_path) as f:
    exec(f.read(), {'__file__': activate_venv_path})


import os
import sys
import warnings
import rasterio
import numpy as np
from datetime import datetime
import cProfile  # noqa: F401
from SarSpectrum import SarSpectrum

"""
GF3_DUMP_DATA() reads the GF3 format SLC data, and write to disk the
DORIS-compatale binary format for DORIS processing.
"""

# suppress NotGeoreferencedWarning
warnings.filterwarnings(
    "ignore", category=rasterio.errors.NotGeoreferencedWarning)  # type: ignore


def gf3_to_data(
    filein: str,
    fileout: str,
    l0: int = None,
    lN: int = None,
    p0: int = None,
    pN: int = None,
) -> tuple:

    if not os.path.exists(filein):
        raise FileNotFoundError("File {} not found!".format(filein))

    with rasterio.open(filein) as src:
        w = src.read()

    if l0 is None:
        l0 = 1
    if lN is None:
        lN = src.height
    if p0 is None:
        p0 = 1
    if pN is None:
        pN = src.width

    with open(fileout, "wb") as fout:
        for ln in range(l0 - 1, lN):
            cdata = np.empty((pN - p0 + 1) * 2, dtype="<i2")
            cdata[0::2] = w[0, ln, p0 - 1: pN]
            cdata[1::2] = w[1, ln, p0 - 1: pN]
            cdata.tofile(fout)

    return lN - l0 + 1, pN - p0 + 1


def gf3_to_res(resFile: str, l0: int, lN: int, p0: int, pN: int) -> bool:

    fileout = "test.slc"

    if resFile is None:
        raise FileNotFoundError()

    # check whether the file exist
    outStream = open(resFile, "a")

    outStream.write("\n")
    outStream.write("**************************************************\n")
    outStream.write("*_Start_crop:			GF3\n")
    outStream.write("**************************************************\n")
    outStream.write("Data_output_file: 	%s\n" % fileout)
    outStream.write("Data_output_format: 			complex_short\n")

    outStream.write("First_line (w.r.t. original_image): 	%s\n" % l0)
    outStream.write("Last_line (w.r.t. original_image): 	%s\n" % lN)
    outStream.write("First_pixel (w.r.t. original_image): 	%s\n" % p0)
    outStream.write("Last_pixel (w.r.t. original_image): 	%s\n" % pN)

    outStream.write("**************************************************\n")
    outStream.write("* End_crop:_NORMAL\n")
    outStream.write("**************************************************\n")

    outStream.write("\n")
    outStream.write("    Current time: {}\n".format(datetime.now))
    outStream.write("\n")

    outStream.close()

    # replace crop tag in result file from 0 (not done) to 1 (done)
    sourceText = "crop:			0"
    replaceText = "crop:			1"
    inputStream = open(resFile, "r")
    textStream = inputStream.read()
    inputStream.close()
    outputStream = open(resFile, "w")
    outputStream.write(textStream.replace(sourceText, replaceText))
    outputStream.close()

    return True


def gf3_dump_data_usage():
    print(
        "\nUsage: python3 gf3_dump_data_usage.py inputfile outputfile l0 lN p0 pN"
    )  # nopep8
    print("  where inputfile        is the input filename")
    print("        outputfile       is the output filename")
    print("        l0               is the first azimuth line (starting at 1)")
    print("        lN               is the last azimuth line")
    print("        p0               is the first range pixel (starting at 1)")
    print("        pN               is the last range pixel")


if __name__ == "__main__":
    try:
        filein = sys.argv[1]
        fileout = sys.argv[2]
    except Exception:
        print("\nError   : Unrecognized input or missing arguments!\n\n")
        gf3_dump_data_usage()
        sys.exit(1)

    if len(sys.argv) == 3:
        l0, lN, p0, pN = None, None, None, None  # type:ignore
    elif len(sys.argv) == 7:
        l0 = int(sys.argv[3])
        lN = int(sys.argv[4])
        p0 = int(sys.argv[5])
        pN = int(sys.argv[6])
    else:
        print("\nError   : Unrecognized input or wrong arguments!\n\n")
        gf3_dump_data_usage()
        sys.exit(1)

    # locate & read ALOS2 file
    az_lines, ra_samples = gf3_to_data(filein, fileout, l0, lN, p0, pN)

    # plot & export quicklook
    sys.stdout.write("Exporting quicklook...")
    if l0 is None and lN is None and p0 is None and pN is None:
        l0: int = 1
        lN: int = az_lines
        p0: int = 1
        pN: int = ra_samples

    # quicklook
    sar_array = SarSpectrum(fileout, pN - p0 + 1, lN - l0 + 1)
    sar_array.read_sar((1, pN - p0 + 1), (1, lN - l0 + 1))
    sar_array.quicklook(fileout + '.png', decimate=10)
    sys.stdout.write(" Done.\n")
