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
        """[summary]
        """        
        self.meta = {}  # meta file, empty dictionary

    def locate_meta(self, directory: str):
        """locate the XML file in the directory.

        Parameters
        ----------
        directory : str
            [description]
        """
        pattern = "GF3*L1A*.meta.xml"        
        self.meta['path'] = locate(pattern, directory)

    def read_meta(self):
        """[summary]
        """        
        
        # e = xml.etree.ElementTree.parse('thefile.xml').getroot()
        # for atype in e.findall('type'):
        #     print(atype.get('foobar'))
        inTree = etree.parse(inputFileName)

        # query syntax for every field
        queryList = {
                    # mission info
                    'mission'             : 'sourceAttributes/satellite',
                    # imageFile file
                    # fullResolutionImageData pole="HH" # inTree.findall('imageAttributes/fullResolutionImageData')[0].text, and more [1] .. [3]
                    'imageFile'           : 'imageAttributes/fullResolutionImageData',
                    #'imageLines'          : 'imageAttributes/rasterAttributes/numberOfLines',
                    'imageLines'          : 'imageAttributes//numberOfLines',
                    'imagePixels'         : 'imageAttributes//numberOfSamplesPerLine',
                    'imageLineSpacing'    : 'imageAttributes//sampledLineSpacing',
                    'imagePixelSpacing'   : 'imageAttributes//sampledPixelSpacing',
                    # volume info
                    #'volFile' : 'productComponents/annotation/file/location/filename', # HARDCODED!!! for radarsat-2
                    # following smt like Level 1B Product, check manual
                    'volID'               : 'productId',
                    'volRef'              : 'documentIdentifier',
                    # product info
                    #productSpec'          : 'generalHeader/referenceDocument',  # TSX
                    'productSpec'         : 'documentIdentifier',
                    'productVolDate'      : 'imageGenerationParameters//processingTime',
                    'productSoftVer'      : 'imageGenerationParameters//softwareVersion',
                    'productDate'         : 'sourceAttributes/rawDataStartTime',
                    'productFacility'     : 'imageGenerationParameters//processingFacility',
                    # scene info
                    #'scenePol'           : 'sourceAttributes/radarParameters/acquisitionType',    # Fine Quad Polarization
                    'scenePol'            : 'sourceAttributes//polarizations',
                    'sceneBeam'           : 'sourceAttributes//beams',
                    'sceneBeamMode'       : 'sourceAttributes/beamModeMnemonic',
                    'list_sceneLat'       : 'imageAttributes/geographicInformation/geolocationGrid/imageTiePoint/geodeticCoordinate/latitude',
                    'list_sceneLon'       : 'imageAttributes/geographicInformation/geolocationGrid/imageTiePoint/geodeticCoordinate/longitude',
                    'sceneRecords'        : 'imageGenerationParameters/sarProcessingInformation/numberOfLinesProcessed',
                    'antennaLookDir'      : 'sourceAttributes//antennaPointing',
                    'missinglines'        : 'sourceAttributes//numberOfMissingLines',
                    # orbit info
                    'orbitABS'            : 'sourceAttributes/orbitAndAttitude//orbitDataFile',
                    'orbitDir'            : 'sourceAttributes//passDirection',
                    'list_orbitTime'      : 'sourceAttributes//stateVector/timeStamp',
                    'list_orbitX'         : 'sourceAttributes//stateVector/xPosition',
                    'list_orbitY'         : 'sourceAttributes//stateVector/yPosition',
                    'list_orbitZ'         : 'sourceAttributes//stateVector/zPosition',
                    'list_orbitXV'        : 'sourceAttributes//stateVector/xVelocity',
                    'list_orbitYV'        : 'sourceAttributes//stateVector/yVelocity',
                    'list_orbitZV'        : 'sourceAttributes//stateVector/zVelocity',
                    # range
                    'list_rangeRSR'       : 'sourceAttributes//adcSamplingRate', # for UF mode there are two subpulses which have to be added together
                    'rangeBW'             : 'imageGenerationParameters//rangeLookBandwidth',
                    'rangeWind'           : 'imageGenerationParameters//rangeWindow/windowName',
                    'rangeWindCoeff'      : 'imageGenerationParameters//rangeWindow/windowCoefficient',
                    'rangeTimePix'        : 'imageGenerationParameters//slantRangeTimeToFirstRangeSample',
                    # azimuth
                    'azimuthPRF'          : 'sourceAttributes//pulseRepetitionFrequency', # for some modes (MF, UF) this value is changed in processing, calculate from other values
                    'azimuthBW'           : 'imageGenerationParameters//azimuthLookBandwidth',
                    'azimuthWind'         : 'imageGenerationParameters//azimuthWindow/windowName',
                    'azimuthWindCoeff'    : 'imageGenerationParameters//azimuthWindow/windowCoefficient',
                    'azimuthTimeFirstLine': 'imageGenerationParameters//zeroDopplerTimeFirstLine',
                    'azimuthTimeLastLine' : 'imageGenerationParameters//zeroDopplerTimeLastLine',
                    # doppler
                    'dopplerTime'         : 'imageGenerationParameters//timeOfDopplerCentroidEstimate',
                    'dopplerCoeff'        : 'imageGenerationParameters//dopplerCentroidCoefficients',
                    # for wavelength computation
                    'radarfreq'           : 'sourceAttributes//radarCenterFrequency',
                    #  wavelength_computed = (0.000000001*SOL/atof(c8freq)) seems more reliable, BK 03/04
                    }


        # get variables and parameters from xml
        container = {}
        for key, value in queryList.iteritems():
            if key.startswith('list_'):
                container[key] = [tag.text for tag in inTree.findall(nsmap_none(value, ns))]
            else:
                container[key] = inTree.findtext(nsmap_none(value, ns))
                if container[key] == None:
                    raise Exception('Path {0} not found in XML'.format(value))

        container['dopplerCoeff'] = container['dopplerCoeff'].split()        


        
        pass

    def export2res():
        """[summary]
        """        
        pass

    def usage():
        """[summary]
        """        
        pass


def locate(pattern:str, root=os.curdir) -> str:
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

