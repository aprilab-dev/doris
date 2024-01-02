import os
venv_path = os.getenv('DORIS_PYTHON3_VENV', None)
if venv_path:
    activate_venv_path = os.path.join(venv_path, 'bin/activate_this.py')
    with open(activate_venv_path) as f:
        exec(f.read(), {'__file__': activate_venv_path})

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.image as img


class SarSpectrum:
    """
    SarSpectrum is a sample class to read binary 2-D SAR (complex) and show
    the spectrum/spectrogram on range/azimuth directions.

    @author: Yuxiao QIN
    @date: 2018-03-17
    """

    def __init__(self, filename, sample, line):
        """
        __INIT__(): read the filename, sample and line from (binary) SAR file

        :param filename: the filename (destination on disk)
        :param sample: sample of the 2D SAR data
        :param line: line of the 2D SAR data
        """
        self.filename = filename
        self.sample = sample
        self.line = line
        self.sar_array = []
        self.norm = 0  # normalization factor

    def read_sar(self, sample_box=(), line_box=()):
        """
        READ_SAR(): read the binary file into a 2D complex array.
        :param sample_box:  the range of sample, tuple.
        :param line_box:    the range of line, tuple
        """

        # Define the box of 2D SAR array
        # Check the correctness of self-defined area
        if not all(sample_box):
            sample_box = (1, self.sample)
        if not all(line_box):
            line_box = (1, self.line)
        if type(sample_box) != tuple or type(line_box) != tuple:
            raise TypeError('SarSpectrum.read_sar(sample_box,line_box): '
                            'parameter SAMPLER_BOX & LINE_BOX must be a tuple!')
        if len(sample_box) != 2 or len(line_box) != 2:
            raise TypeError('SarSpectrum.read_sar(sample_box,line_box): '
                            'tuple SAMPLER_BOX & LINE_BOX must have two and '
                            'only two elements indicating the starting and '
                            'ending lines/samples of your region!')
        if sample_box[0] < 1 or sample_box[1] > self.sample:
            raise ValueError('SarSpectrum.read_sar(): Self-defined sample '
                             'is out of the min/max sample of SAR array! ')
        if line_box[0] < 1 or line_box[1] > self.line:
            raise ValueError('SarSpectrum.read_sar(): Self-defined line '
                             'is out of the min/max line of SAR array! ')
        if sample_box[1] < sample_box[0] or line_box[1] < line_box[0]:
            raise ValueError('SarSpectrum.read_sar(sample_box,line_box): '
                             'second value must be greater than the first! ')

        # pre-allocate 2D complex array
        sample_len = sample_box[1] - sample_box[0] + 1
        line_len = line_box[1] - line_box[0] + 1
        self.sar_array = np.zeros((sample_len, line_len), dtype='complex64')

        # define if the data is complex (is 2 compared with real is 1)
        if_complex = 2
        # The binary type is "single" and takes up to 4 bytes
        binary_byte = 2
        # Data type
        dtype = np.dtype('i2')  # 32-bit unsigned integer

        # Read the binary file
        j_line = 0
        with open(self.filename, 'rb') as sar_arr_tmp:
            for j in range(line_box[0]-1, line_box[1]):
                # calculate current line offset
                offset = (j * self.sample + (sample_box[0] - 1)) * \
                         if_complex * binary_byte
                sar_arr_tmp.seek(offset)
                # read
                cdata = np.fromfile(sar_arr_tmp, dtype, sample_len * 2)
                # convert to complex number
                if if_complex == 2:
                    cdata = cdata[0::2] + 1j * cdata[1::2]
                # assign to self class
                self.sar_array[:, j_line] = cdata
                j_line += 1
                self.norm += np.sum(np.absolute(cdata))
        self.norm /= sample_len * line_len
        # Update sample and line
        self.sample = sample_len
        self.line = line_len

    def plot_sar(self, plot_option='abs'):
        """
        PLOT_SAR(): plot the SAR imagery
        :param plot_option: 'abs' or 'phase'
        """

        fig = plt.figure()
        ax = fig.add_subplot(111)

        if plot_option == 'abs':
            # plot the amplitude
            plt.imshow(np.absolute(self.sar_array)/self.norm, vmax=3)
            ax.set_title('Amplitude of SAR Imagery')

        elif plot_option == 'phase':
            # plot the phase
            plt.imshow(np.angle(self.sar_array))
            ax.set_title('Phase of SAR Imagery')

        ax.set_xlabel('Azimuth [px]')
        ax.set_ylabel('Range [px]')
        ax.set_aspect('equal')
        plt.colorbar()
        plt.show()

    def quicklook(self, outfile: str = 'quicklook.png', decimate: int = 1):
        quicklook = self.sar_array[::decimate, ::decimate]  # type: ignore
        img.imsave(outfile, np.abs(quicklook) * decimate / self.norm,
                   vmin=0, vmax=10)

    def spectrum(self, direction='2d'):
        """
        SPECTRUM() is going to display the spectrum on the choosen direction.
        SPECTRUM('azimuth'): show the AVERAGED spectrum on azimuth direction.
        SPECTRUM('range'): show the AVERAGED spectrum on range direction.
        SPECTRUM('2d'): show the 2D spectrum

        :param direction: 'azimuth', 'range' or '2d'
        """

        # Normalized tick label
        tick_label = [np.array2string(i, precision=1, suppress_small=True)
                      for i in np.linspace(-0.5, 0.5, 11)]
        tick_label[tick_label.index("0.")] = '0'  # change '0.' to '0'

        # 2D FFT
        if direction == '2d':
            # perform fft
            spectra = np.fft.fft2(self.sar_array)
            spectra = np.fft.fftshift(spectra)

            # Plot 2D FFT
            fig = plt.figure()
            ax = fig.add_subplot(111)
            cax = plt.imshow(np.absolute(spectra))
            ax.set_title('2D Spectrum of target SAR image')
            ax.set_xlabel('Normalized azimuth frequency')
            ax.set_ylabel('Normalized range frequency')
            ax.set_xticks(np.linspace(0, self.line, 11))
            ax.set_xticklabels(tick_label)
            ax.set_yticks(np.linspace(0, self.sample, 11))
            ax.set_yticklabels(tick_label)
            # colorbar
            cbar = plt.colorbar(cax, ticks=[1, np.max(np.absolute(spectra))])
            cbar.ax.set_yticklabels(['0', '1'])
            cbar.set_label('Normalized amplitude of spectrum')
            plt.show()

        else:
            if direction == 'azimuth':
                spectra_1d = np.zeros(self.line)
                i_total = self.sample

            elif direction == 'range':
                spectra_1d = np.zeros(self.sample)
                i_total = self.line

            # Calculate Average Specturm
            for m in range(0, i_total):
                if direction == 'azimuth':
                    spectra = np.fft.fft(self.sar_array[m, :])
                elif direction == 'range':
                    spectra = np.fft.fft(self.sar_array[:, m])

                spectra = np.absolute(np.fft.fftshift(spectra))
                # average (or sum, no difference between two)
                spectra_1d += spectra

            # plot
            fig = plt.figure()
            ax = fig.add_subplot(111)
            # noinspection PyUnboundLocalVariable
            if direction == 'azimuth':
                plt.plot(np.arange(0, self.line), spectra_1d)
                ax.set_title('Averaged Azimuth Spectrum of target SAR')
                ax.set_xlabel('Normalized azimuth frequency')
                ax.set_xticks(np.linspace(0, self.line, 11))
            elif direction == 'range':
                plt.plot(np.arange(0, self.sample), spectra_1d)
                ax.set_title('Averaged Range Spectrum of target SAR')
                ax.set_xlabel('Normalized range frequency')
                ax.set_xticks(np.linspace(0, self.sample, 11))

            ax.set_xticklabels(tick_label)
            ax.set_yticks([np.min(spectra_1d), np.max(spectra_1d)])
            ax.set_yticklabels(['0', '1'])
            ax.set_ylabel('Normalized Amplitude')
            ax.grid(b=True, which='major')
            ax.minorticks_on()
            ax.grid(which='minor', linestyle=':', linewidth='0.5', color='blue')
            plt.show()

    def spectrogram(self, direction='azimuth', fft_size=256, step=16,
                    sampling=20):
        """
        SPECTROGRAM() plots the spectrogram on chosen direction.
        :param direction: 'azimuth' or 'range'
        :param fft_size: FFT and Window size for spectrogram
        :param step: spectrogram step
        :param sampling: the sampling gap of lines used for averaging the
        spectrogram
        :return:
        """

        # Check the input
        if direction == 'azimuth':
            if fft_size > self.sample:
                raise ValueError('SarSpectrum.spectrogram(): '
                                 'fft_size is %d and is greater than the '
                                 'sample length (%d) of your SAR image! '
                                 % (fft_size, self.sample))
        elif direction == 'range':
            if fft_size > self.line:
                raise ValueError('SarSpectrum.spectrogram(): '
                                 'fft_size is %d and is greater than the line '
                                 'length (%d) of your SAR image! '
                                 % (fft_size, self.sample))

        elif direction == 'range':
            i_total = self.line

        # Calculate Average Specturm
        if direction == 'azimuth':
            i_total = self.sample

        elif direction == 'range':
            i_total = self.line

        for m in range(0, i_total, sampling):
            if direction == 'azimuth':
                cdata_tmp = self.sar_array[m, :]
            elif direction == 'range':
                cdata_tmp = self.sar_array[:, m]

            # Calculate Spectrogram
            fig = plt.figure()
            (spectro_tmp, *arg) = plt.specgram(cdata_tmp, NFFT=fft_size, Fs=1,
                                               noverlap=fft_size-step,
                                               pad_to=fft_size,
                                               sides='twosided')
            plt.close(fig)  # do not display figure

            # Calculate Average
            if m == 0:
                spectro = spectro_tmp
            else:
                spectro += spectro_tmp

        # Plot Spectrogram
        fig = plt.figure(direction)
        ax = fig.add_subplot(111)
        cax = plt.imshow(np.absolute(spectro))
        if direction == 'azimuth':
            ax.set_title('Average Azimuth Spectrogram of target SAR')
            ax.set_xlabel('Azimuth [steps: %d]' % step)
            tick_label = [str(int(i)) for i in np.linspace(fft_size,
                                                           self.line, 7)]
        elif direction == 'range':
            ax.set_title('Average Range Spectrogram of target SAR')
            ax.set_xlabel('Range [steps: %d]' % step)
            tick_label = [str(int(i)) for i in np.linspace(fft_size,
                                                           self.sample, 7)]

        ax.set_xticklabels(tick_label)
        ax.set_xticks(np.linspace(0, len(spectro[0, :]-1), 7))
        ax.set_ylabel('Normalized Frequency')
        ax.set_yticks([1, fft_size/2, fft_size])
        ax.set_yticklabels(['-0.5', '0', '0.5'])

        # colorbar
        cbar = plt.colorbar(cax, ticks=[np.min(np.absolute(spectro)),
                                        np.max(np.absolute(spectro))])
        cbar.ax.set_yticklabels(['0', '1'])
        cbar.set_label('Normalized amplitude of spectrum')
        ax.set_aspect(aspect='auto')
        plt.show()
