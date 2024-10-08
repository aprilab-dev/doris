#!/usr/bin/env python3

import os
venv_path = os.getenv('DORIS_PYTHON3_VENV', None)
if venv_path:
    activate_venv_path = os.path.join(venv_path, 'bin/activate_this.py')
    with open(activate_venv_path) as f:
        exec(f.read(), {'__file__': activate_venv_path})
import os
import sys
import re
import struct
import math
import numpy as np
from datetime import datetime
from datetime import timedelta


class ALOS2:
    """
    ALOS2 is used to read ALOS2 meta data and SLC data that is compatible with
    DORIS input.


    author = Yuxiao QIN
    date = 2019-Jan
    """

    # speed of light
    c = 299792458

    def __init__(self, filename=''):
        # initialization of class properties
        self.file = dict(leader=None, image=None)  # file pointer
        self.meta = {}  # meta file, empty dictionary

        # predefinition of certain fields in meta
        self.meta['Product type specifier'] = 'ALOS2'
        self.meta['SAR_PROCESSOR'] = 'Japan JAXA'

    def locate_file(self, directory):
        """
        LOCATE_FILE(): locate the VOL*, LED* and IMG* file based on
         directory name.
        :directory: the directory of a single SLC folder.
        """

        for file in os.listdir(directory):
            if re.match('LED-ALOS2', file):  # leader
                self.file['leader'] = os.path.join(directory, file)
            elif re.match('IMG-(H|V)(H|V)-ALOS2', file):  # slc
                self.file['image'] = os.path.join(directory, file)
            elif re.match('VOL-ALOS2', file):  # volume
                self.file['volume'] = os.path.join(directory, file)

    def read_leader(self):
        if os.path.exists(self.file['leader']):
            fid = open(self.file['leader'], 'rb')  # ALOS2: Big Endian

            """ Leader file """
            (_, self.meta['Leader file']) = os.path.split(self.file['leader'])

            """ Get the location of summary/facility/platform... file """
            fid.seek(180)  # read 180 to 336
            data_record_info = fid.read(156).decode('ascii')  # bytes to char
            record_number = []
            record_length = []
            for i in range(0, len(data_record_info), 12):
                record_number.append(int(data_record_info[i:i+6]))
                record_length.append(int(data_record_info[i+7:i+12]))

            """ summary record """
            fid.seek(720)
            summary_record = fid.read(record_number[0]*record_length[0])

            """ wavelenth """
            self.meta['Radar_wavelength (m)'] = float(summary_record[500:516])

            """ incidence angle at scene center"""
            self.meta['incidence angle (deg)'] = float(summary_record[484:492])

            """ Range_sampling_rate (computed, MHz) """
            self.meta['Range_sampling_rate (computed, MHz)'] = (
                float(summary_record[710:726]))

            """ Total_range_band_width (MHz) """
            self.meta['Total_range_band_width (MHz)'] = (
                float(summary_record[1222:1238])) * 1e-6  # Hz -> MHz

            """ Pulse_Repetition_Frequency (computed, Hz) """
            self.meta['Pulse_Repetition_Frequency (computed, Hz)'] = (
                float(summary_record[934:950])) * 1e-3  # mHz -> Hz

            """ Total_azimuth_band_width (Hz) """
            self.meta['Total_azimuth_band_width (Hz)'] = (
                float(summary_record[1238:1254]))

            """ Range Spacing / Azimuth Spacing """
            self.meta['range spacing'] = float(summary_record[1702:1718])
            self.meta['azimuth spacing'] = float(summary_record[1686:1702])

            """
            Weighting
            Yes, you are right, they use a rectangle window.
            Who knows what they are thinking???
            """
            self.meta['Weighting_range'] = 'RECTANGLE'
            self.meta['Weighting_azimuth'] = 'RECTANGLE'

            """
            Along-track Doppler Centroid [Hz/pixel]
            F_dc(t_az) = A_coef_0 + A_coef_0 * t_az + A_coef_0 * t_az^2
            """
            self.meta['Atrack_f_DC_constant (Hz, early edge)'] = (
                float(summary_record[1414:1430]))
            self.meta['Atrack_f_DC_linear (Hz/pixel, early edge)'] = (
                float(summary_record[1430:1446]))
            self.meta['Atrack_f_DC_quadratic (Hz/pixel^2, early edge)'] = (
                float(summary_record[1446:1462]))

            """
            Cross-track Doppler Centroid [Hz/s]
            F_dc(t_rg)= X_coef_0 + X_coef_0 * t_rg + X_coef_0 * t_rg^2
            """
            rg_space_2_time = self.meta['range spacing'] * 2 / self.c
            self.meta['Xtrack_f_DC_constant (Hz, early edge)'] = (
                float(summary_record[1478:1494]))
            self.meta['Xtrack_f_DC_linear (Hz/s, early edge)'] = (
                float(summary_record[1494:1510])) / rg_space_2_time
            self.meta['Xtrack_f_DC_quadratic (Hz/s/s, early edge)'] = (
                float(summary_record[1510:1526])) / (rg_space_2_time ** 2)

            """ Sensor platform mission identifer """
            self.meta['Sensor platform mission identifer'] = (
                summary_record[396:401].decode("ascii"))

            """ Orbital Pass """
            orbit_pass = summary_record[1534:1540].decode("ascii") + 'ING'

            """ Orbit & Frame Number"""
            orbit_number = summary_record[25:30].decode("ascii")
            frame_number = summary_record[30:34].decode("ascii")

            self.meta['Scene identification'] = (
                'Orbit: ' + orbit_number + ' ' + orbit_pass + ' Mode: ' +
                self.meta['observation_mode'])

            """ platform record """
            fid.seek(720 + record_number[0]*record_length[0] +
                     record_number[1]*record_length[1])
            platform_record = fid.read(record_number[2]*record_length[2])

            npoints = int(platform_record[140:144])
            t1 = float(platform_record[160:182])
            dt = float(platform_record[182:204])

            self.meta['Orbit_n_pts'] = npoints
            self.meta['Orbit Time'] = np.arange(t1, t1 + dt*npoints, dt).tolist()  # nopep8
            self.meta['Orbit X'] = []
            self.meta['Orbit Y'] = []
            self.meta['Orbit Z'] = []

            for j in range(0, npoints):
                offset = j*132
                self.meta['Orbit X'].append(float(platform_record[offset + 386:offset + 408]))  # nopep8
                self.meta['Orbit Y'].append(float(platform_record[offset + 408:offset + 430]))  # nopep8
                self.meta['Orbit Z'].append(float(platform_record[offset + 430:offset + 452]))  # nopep8

    def read_volume(self):
        if os.path.exists(self.file['volume']):
            fid = open(self.file['volume'], 'rb')  # ALOS2: Big Endian

            """ Volume_ID & Volume file """
            (_, self.meta['Volume file']) = os.path.split(self.file['volume'])
            fid.seek(360+27)
            volumn_file_char = fid.read(1).decode('ascii')
            if volumn_file_char == 'B':
                self.meta['Volume_ID'] = 'Level 1.1'
            else:
                raise NotImplementedError(
                    "Data processing level not recognized! "
                    "Only ALOS-2 Level 1.1 is supported!")

            """ Get the polarization number """
            fid.seek(163)
            polar = int(fid.read(1))

            """ Product ID/Volume_set_identifier """
            fid.seek(360+360*polar+24)
            observation_mode = fid.read(3).decode('ascii')
            self.meta['observation_mode'] = observation_mode
            if observation_mode == 'UBS':
                self.meta['Volume_set_identifier'] = (
                    'Ultra-fine mode (single pol)')
            elif observation_mode == 'UBD':
                self.meta['Volume_set_identifier'] = (
                    'Ultra-fine mode (dual pol)')
            elif observation_mode == 'HBS':
                self.meta['Volume_set_identifier'] = (
                    'High-sensitive mode (single pol)')
            elif observation_mode == 'HBD':
                self.meta['Volume_set_identifier'] = (
                    'High-sensitive mode (dual pol)')
            elif observation_mode == 'HBQ':
                self.meta['Volume_set_identifier'] = (
                    'High-sensitive mode (full/quad pol)')
            elif observation_mode == 'FBS':
                self.meta['Volume_set_identifier'] = (
                    'Fine mode (single pol)')
            elif observation_mode == 'FBD':
                self.meta['Volume_set_identifier'] = (
                    'Fine mode (dual pol)')
            elif observation_mode == 'FBQ':
                self.meta['Volume_set_identifier'] = (
                    'Fine mode (full/quad pol)')
            else:
                raise NotImplementedError(
                    "ALOS2 observation mode {} is not yet implemented!"
                    .format(observation_mode))

            """ Logical volume generating facility """
            fid.seek(360+360*polar+81)
            process_facility = fid.read(4).decode('ascii')
            if process_facility == 'SCMO':
                self.meta['Logical volume generating facility'] = (
                    'Japan JAXA Spacecraft Control Mission Operation system')
            elif process_facility == 'EICS':
                self.meta['Logical volume generating facility'] = (
                    'Japan JAXA Earth Intelligence Collection and Shearing system')  # nopep8
            else:
                raise NotImplementedError(
                    "ALOS2 processing facility {} is not recognized!"
                    .format(process_facility))

            """ Location and date/time of product creation """
            fid.seek(2, os.SEEK_CUR)
            process_date = fid.read(15).decode('ascii')
            process_date = (datetime
                            .strptime(process_date, "%Y%m%d %H%M%S")
                            .strftime("%Y-%m-%dT%H:%M:%SZ"))
            self.meta['Location and date/time of product creation'] = process_date  # nopep8

            """ Logical volume creation date """
            fid.seek(112)
            volume_create_date = fid.read(14).decode('ascii')
            volume_create_date = (datetime
                                  .strptime(volume_create_date, "%Y%m%d%H%M%S")
                                  .strftime("%Y-%m-%dT%H:%M:%SZ"))
            self.meta['Logical volume creation date'] = volume_create_date

    def read_img(self):
        if os.path.exists(self.file['image']):
            fid = open(self.file['image'], 'rb')

            # lines and pixels
            fid.seek(186)
            self.meta['size_of_each_line'] = int(fid.read(6))
            fid.seek(236)
            self.meta['Number_of_lines_original'] = int(fid.read(8))  # azimuth
            self.meta['(Check)Number of records in ref. file'] = (
                self.meta['Number_of_lines_original'])
            fid.seek(248)
            self.meta['Number_of_pixels_original'] = int(fid.read(8))  # range

            # filename and format
            (_, self.meta['Datafile']) = os.path.split(self.file['image'])
            fid.seek(16)
            self.meta['Dataformat'] = fid.read(8).decode('ascii')

            # first azimuth line
            fid.seek(720+36)
            acquisition_year, *_ = struct.unpack('>i', fid.read(4))
            acquisition_day, *_ = struct.unpack('>i', fid.read(4))
            acquisition_sec, *_ = struct.unpack('>i', fid.read(4))

            d = (datetime(acquisition_year, 1, 1) +
                 timedelta(days=(acquisition_day - 1),
                           milliseconds=acquisition_sec))
            self.meta['First_pixel_azimuth_time (UTC)'] = (
                datetime.strftime(d, "%d-%b-%Y %H:%M:%S.%f"))

            # two way slant range time
            fid.seek(720+116)
            two_way_slant_range, *_ = struct.unpack('>i', fid.read(4))
            self.meta['Range_time_to_first_pixel (2way) (ms)'] = (
                two_way_slant_range * 2 * 1000 / self.c)

            # center lon/lat
            center_line = math.ceil(self.meta['Number_of_lines_original'] / 2)
            fid.seek(720+(center_line-1)*self.meta['size_of_each_line']+196)
            center_lat, *_ = struct.unpack('>i', fid.read(4))
            center_lat *= 1e-06
            fid.seek(8, os.SEEK_CUR)
            center_lon, *_ = struct.unpack('>i', fid.read(4))
            center_lon *= 1e-06
            self.meta['Scene_centre_latitude'] = center_lat
            self.meta['Scene_centre_longitude'] = center_lon
            self.meta['Scene location'] = (
                'lat: ' + str(center_lat) + ' lon: ' + str(center_lon))

    def export2res(self):
        keys_lead = ('Volume file',
                     'Volume_ID',
                     'Volume_set_identifier',
                     '(Check)Number of records in ref. file',
                     'SAR_PROCESSOR',
                     'Product type specifier',
                     'Logical volume generating facility',
                     'Logical volume creation date',
                     'Location and date/time of product creation',
                     'Scene identification',
                     'Scene location',
                     'Leader file',
                     'Sensor platform mission identifer',
                     'Scene_centre_latitude',
                     'Scene_centre_longitude',
                     'Radar_wavelength (m)',
                     'First_pixel_azimuth_time (UTC)',
                     'Pulse_Repetition_Frequency (computed, Hz)',
                     'Total_azimuth_band_width (Hz)',
                     'Weighting_azimuth',
                     'Xtrack_f_DC_constant (Hz, early edge)',
                     'Xtrack_f_DC_linear (Hz/s, early edge)',
                     'Xtrack_f_DC_quadratic (Hz/s/s, early edge)',
                     'Range_time_to_first_pixel (2way) (ms)',
                     'Range_sampling_rate (computed, MHz)',
                     'Total_range_band_width (MHz)',
                     'Weighting_range')

        keys_file = ('Datafile',
                     'Dataformat',
                     'Number_of_lines_original',
                     'Number_of_pixels_original')

        print('\nalos2_dump_header2doris.py v0.1, doris software, 2019\n')
        print('**************************************************************')
        print('*_Start_readfiles:')
        print('**************************************************************')

        for keys in keys_lead:
            print('{:<50}\t{}'.format(keys+':', self.meta[keys]))

        print('')
        print('**************************************************************')
        for keys in keys_file:
            print('{:<50}\t{}'.format(keys+':', self.meta[keys]))

        print('**************************************************************')
        print('* End_readfiles:_NORMAL')
        print('**************************************************************')
        print('')
        print('')
        print('**************************************************************')
        print('*_Start_leader_datapoints')
        print('**************************************************************')
        print(' t(s)		X(m)		Y(m)		Z(m)')
        print('NUMBER_OF_DATAPOINTS: 			{}'.format(self.meta['Orbit_n_pts']))  # nopep8
        print('')

        for i in range(0, self.meta['Orbit_n_pts']):

            x, y, z = ['{:7.6f}'.format(e) for e in (
                self.meta['Orbit X'][i],
                self.meta['Orbit Y'][i],
                self.meta['Orbit Z'][i])]  # format in a nicer way

            print(' {:>7} {:>15} {:>15} {:>15}'.format(
                self.meta['Orbit Time'][i], x, y, z))

        print('\n')
        print('**************************************************************')
        print('* End_leader_datapoints:_NORMAL')
        print('**************************************************************')

    def usage():
        print('INFO    : @(#)ALOS2 for Doris, Author: Q')
        print('\n')
        print('Usage   : python alos2_dump_header2doris.py leadfile volfile datfile')  # nopep8
        print('          - `leadfile` is the ALOS2 leader file.')
        print('          - `volfile` is the ALOS2 volume file.')
        print('          - `datfile` is the ALOS2 data file.')
        print('\n')
        print('This software is part of Doris InSAR software package.\n')


if __name__ == "__main__":
    alos2_example = ALOS2()

    # figure out the input parameters.
    if len(sys.argv) != 4:
        print('\nError   : Unrecognized input or missing arguments!\n\n')
        alos2_example.usage()
        sys.exit(1)
    try:
        lead_file = sys.argv[1]
        vol_file = sys.argv[2]
        dat_file = sys.argv[3]
    except:
        print('\nError   : Unrecognized input or missing arguments!\n\n')
        alos2_example.usage()
        sys.exit(1)

    # read
    alos2_example.file['leader'] = lead_file
    alos2_example.file['volume'] = vol_file
    alos2_example.file['image'] = dat_file

    alos2_example.read_volume()
    alos2_example.read_img()
    alos2_example.read_leader()

    # print
    alos2_example.export2res()
