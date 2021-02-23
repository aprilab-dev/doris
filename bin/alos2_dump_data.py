#!/usr/bin/env python3

"""
ALOS2_DUMP_DATA() reads the ALOS2 CEOS format SLC data, and write to disk the
DORIS-compatale binary format for DORIS processing.

Till 2019-Jan, gdal (2.3.3) does not support ALOS-2 L1.1 CEOS format data.
Hence, unlike the TSX & RS2 script, ALOS2 do not use gdal for reading. The
script **is** largely adopted from CSK_DUMP_DATA().

author = Yuxiao QIN
date = 2019-Jan
"""

import os
venv_path = os.getenv('DORIS_PYTHON3_VENV', None)
if venv_path:
    activate_venv_path = os.path.join(venv_path, 'bin/activate_this.py')
    with open(activate_venv_path) as f:
        exec(f.read(), {'__file__': activate_venv_path})

import os
import sys
import numpy as np
from alos2_dump_header2doris import ALOS2
from datetime import datetime


"""
ALOS2_2_DATA():
write the data in Complex Short format (CInt16)
"""


def alos2_2_data(input_filename, output_filename, l0, lN, p0, pN):

    if os.path.exists(input_filename):
        fid = open(input_filename, 'rb')
    else:
        raise FileNotFoundError(
            "File {} not found!".format(input_filename))

    fid.seek(186)
    line_size = int(fid.read(4))  # noqa
    fid.seek(236)
    az_lines = int(fid.read(8))
    fid.seek(248)
    ra_samples = int(fid.read(8))
    fid.close()

    if l0 is None and lN is None and p0 is None and pN is None:
        l0 = 1
        lN = az_lines
        p0 = 1
        pN = ra_samples

    # float, 4 bytes, big endian
    dtype = np.dtype('>f4')  # f4 is float32 (4*8=32.)

    # Write
    fout = open(output_filename, 'wb')

    count = 0
    for az in range(l0-1, lN):
        """
        offset:
        header: 720 bytes of offset.
        each line: 544 bytes of meta file per line.
        each line is (ra_samples * 4 * 2 + 544) bytes.
        """
        offset = 720 + az * (ra_samples * 2 * 4 + 544) + 544 + (p0 - 1) * 2 * 4
        # read
        cdata = np.memmap(input_filename, dtype=dtype, offset=offset, mode='r',
                          shape=(1, (pN - p0 + 1) * 2))

        ## Convert to doris format: complex short (signed integer 2 bytes*2 complex)
        #icdata = cdata/2000  # divided by 100 to avoid OVERFLOW
        #if icdata.max() > 32767 or icdata.min() < -32768:
        #    raise OverflowError("Max/Min Value Overflow 2 bytes signed integer!")
        #icdata = icdata.astype(dtype='i2')
        ## write to disk, complex short format (CInt16)
        #icdata.tofile(fout)

        ## Convert to little endian
        cdata = cdata.astype(dtype='<f4')

        ## Write to disk, complex float32 format (cpxfloat32)
        cdata.tofile(fout)


        # Just for printing progress.
        if az % round((lN-l0+1)/10) == 0 and count < 10:
            sys.stdout.write('%s...' % (count*10))
            count += 1

    sys.stdout.write("100% -- done.\n")
    fid.close()
    return (az_lines, ra_samples)


def alos2_2_res(resFile, l0, lN, p0, pN):

    output_filename = ('/home/yuxiao/insar/insarst01/software/doris/'
                       'doris_alos2/ALOS2_sample_data/chiba/1000000000'
                       '_001001_ALOS2076070700-151020/master.slc')

    # Only write when .res file exist.
    if resFile is not None:

        # check whether the file exist
        outStream = open(resFile, 'a')

        outStream.write('\n')
        outStream.write('**************************************************\n')
        outStream.write('*_Start_crop:			ALOS2\n')
        outStream.write('**************************************************\n')
        outStream.write('Data_output_file: 	%s\n' % output_filename)
        #outStream.write('Data_output_format: 			complex_short\n')
        outStream.write('Data_output_format: 			complex_real4\n')

        outStream.write('First_line (w.r.t. original_image): 	%s\n' % l0)
        outStream.write('Last_line (w.r.t. original_image): 	%s\n' % lN)
        outStream.write('First_pixel (w.r.t. original_image): 	%s\n' % p0)
        outStream.write('Last_pixel (w.r.t. original_image): 	%s\n' % pN)

        outStream.write('**************************************************\n')
        outStream.write('* End_crop:_NORMAL\n')
        outStream.write('**************************************************\n')

        outStream.write('\n')
        outStream.write('    Current time: {}\n'.format(datetime.now))
        outStream.write('\n')

        outStream.close()

        # replace crop tag in result file from 0 (not done) to 1 (done)
        sourceText = "crop:			0"
        replaceText = "crop:			1"
        inputStream = open(resFile, 'r')
        textStream = inputStream.read()
        inputStream.close()
        outputStream = open(resFile, "w")
        outputStream.write(textStream.replace(sourceText, replaceText))
        outputStream.close()


def alos2_dump_data_usage():
    print('\nUsage: python3 alos2_dump_data_usage.py inputfile outputfile l0 lN p0 pN')  # nopep8
    print('  where inputfile        is the input filename')
    print('        outputfile       is the output filename')
    print('        l0               is the first azimuth line (starting at 1)')
    print('        lN               is the last azimuth line')
    print('        p0               is the first range pixel (starting at 1)')
    print('        pN               is the last range pixel')


if __name__ == "__main__":
    # initialize
    alos2_example = ALOS2()

    # figure out the input parameters.
    try:
        input_filename = sys.argv[1]
        output_filename = sys.argv[2]
    except:
        print('\nError   : Unrecognized input or missing arguments!\n\n')
        alos2_dump_data_usage()
        sys.exit(1)

    if len(sys.argv) == 3:
        l0 = None
        lN = None
        p0 = None
        pN = None
    elif len(sys.argv) == 7:
        l0 = int(sys.argv[3])
        lN = int(sys.argv[4])
        p0 = int(sys.argv[5])
        pN = int(sys.argv[6])
    else:
        print('\nError   : Unrecognized input or wrong arguments!\n\n')
        alos2_dump_data_usage()
        sys.exit(1)

    # locate & read ALOS2 file
    (az_lines, ra_samples) = alos2_2_data(
        input_filename, output_filename, l0, lN, p0, pN)

    # plot & export quicklook
    sys.stdout.write("Exporting quicklook...")
    if l0 is None and lN is None and p0 is None and pN is None:
        l0 = 1
        lN = az_lines
        p0 = 1
        pN = ra_samples

    # sar_array = SarSpectrum(output_filename, pN-p0+1, lN-l0+1)
    # sar_array.read_sar((1, pN-p0+1), (1, lN-l0+1))  # read
    # sar_array.quicklook(output_filename+'.png')
    # sys.stdout.write(" Done.\n")
