#!/usr/bin/env python3

import os
activate_venv_path = os.path.join('/home/yuxiao/.virtualenvs/doris/', 'bin/activate_this.py')
with open(activate_venv_path) as f:
    exec(f.read(), {'__file__': activate_venv_path})


import os
import sys
import h5py
import numpy as np
from datetime import datetime
from SarSpectrum import SarSpectrum


def fc1_to_data(
    filein: str,
    fileout: str,
    l0: int = 0,
    ln: int = 0,
    p0: int = 0,
    pn: int = 0,
) -> tuple:
    """Read TY FC1 SLC data. """

    if not os.path.exists(filein):
        raise FileNotFoundError(f"File {filein} not found!")

    with h5py.File(filein, 'r') as f, open(fileout, "wb") as fout:

        l0 = l0 or 1
        ln = ln or f["number_of_azimuth_samples"][()]
        p0 = p0 or 1
        pn = pn or f["number_of_range_samples"][()]

        cdata_i = f["s_i"][:]
        cdata_q = f["s_q"][:]

        for line in range(l0 - 1, ln):
            cdata = np.empty((pn - p0 + 1) * 2, dtype="<i2")
            cdata[0::2] = cdata_i[line, p0 - 1: pn]
            cdata[1::2] = cdata_q[line, p0 - 1: pn]
            cdata.tofile(fout)

    return ln - l0 + 1, pn - p0 + 1


def fc1_to_res(resFile: str, l0: int, lN: int, p0: int, pN: int) -> bool:

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


def fc1_dump_data_usage():
    """A general help message for fc1_dump_data.py"""
    print(
        "\nUsage: python3 gf3_dump_data_usage.py inputfile outputfile l0 lN p0 pN"
    )
    print("  where inputfile        is the input filename")
    print("        outputfile       is the output filename")
    print("        l0               is the first azimuth line (starting at 1)")
    print("        lN               is the last azimuth line")
    print("        p0               is the first range pixel (starting at 1)")
    print("        pN               is the last range pixel")


if __name__ == "__main__":
    try:
        fin = sys.argv[1]
        fout = sys.argv[2]
    except IndexError:
        print("\nError   : Unrecognized input or missing arguments!\n\n")
        fc1_dump_data_usage()
        sys.exit(1)

    if len(sys.argv) == 3:
        lstart, lend, pstart, pend = 0, 0, 0, 0
    elif len(sys.argv) == 7:
        lstart = int(sys.argv[3])
        lend = int(sys.argv[4])
        pstart = int(sys.argv[5])
        pend = int(sys.argv[6])
    else:
        print("\nError   : Unrecognized input or wrong arguments!\n\n")
        fc1_dump_data_usage()
        sys.exit(1)

    # locate & read ALOS2 file
    az_lines, ra_samples = fc1_to_data(fin, fout, lstart, lend, pstart, pend)


    # plot & export quicklook
    sys.stdout.write("Exporting quicklook...")

    # quicklook
    sar_array = SarSpectrum(fout, ra_samples, az_lines)
    sar_array.read_sar((1, ra_samples), (1, az_lines))
    sar_array.quicklook(fout + '.png', decimate=10)
    sys.stdout.write(" Done.\n")
