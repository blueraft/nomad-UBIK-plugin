#
# Copyright The NOMAD Authors.
#
# This file is part of NOMAD. See https://nomad-lab.eu for further info.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

from typing import (
    TYPE_CHECKING,
)

if TYPE_CHECKING:
    from nomad.datamodel.datamodel import (
        EntryArchive,
    )
    from structlog.stdlib import (
        BoundLogger,
    )

from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    dict,
)

import numpy as np
from nomad.datamodel.data import (
    ArchiveSection,
    EntryData,
)
from nomad.datamodel.metainfo.annotations import (
    ELNAnnotation,
    ELNComponentEnum,
)
from nomad.datamodel.metainfo.basesections import (
    CompositeSystemReference,
    Measurement,
    MeasurementResult,
    ReadableIdentifiers,
)
from nomad.datamodel.results import (
    ElementalComposition,
    Properties,
    Results,
    StructuralProperties,
)
from nomad.metainfo import (
    Datetime,
    Package,
    Quantity,
    Section,
    SubSection,
)
from nomad_measurements import (
    NOMADMeasurementsCategory,
)
from nomad_measurements.utils import merge_sections

from nomad_ubik_plugin.schema_packages import XRFreader

if TYPE_CHECKING:
    from structlog.stdlib import BoundLogger


m_package = Package(name='nomad_xrf')


class XRFElementalComposition(ElementalComposition):
    """
    Section extending ElementalComposition with XRF relevant properties.
    """

    line = Quantity(
        type=str,
        a_eln=ELNAnnotation(component=ELNComponentEnum.StringEditQuantity),
        description='Elemental line used for element analysis',
    )

    intensity_peak = Quantity(
        type=np.dtype(np.float64),
        a_eln=ELNAnnotation(component=ELNComponentEnum.NumberEditQuantity),
        description='Intensity of the element peak',
    )

    intensity_background = Quantity(
        type=np.dtype(np.float64),
        a_eln=ELNAnnotation(component=ELNComponentEnum.NumberEditQuantity),
        description='Intensity of the background sourrounding the element peak',
    )

    intensity_background_2 = Quantity(
        type=np.dtype(np.float64),
        a_eln=ELNAnnotation(component=ELNComponentEnum.NumberEditQuantity),
        description='Optional 2nd backgound intensity',
    )


class XRFLayer(StructuralProperties):
    """
    Section containing the properties of a layer in an X-ray fluorescence measurement.
    """

    # TODO: Add a kind of order to the layers

    name = Quantity(
        type=str,
        a_eln=dict(component='StringEditQuantity'),
    )

    thickness = Quantity(
        type=np.dtype(np.float64),
        unit=('nm'),
        a_eln=dict(component='NumberEditQuantity', defaultDisplayUnit='nm'),
    )

    elements = SubSection(section_def=XRFElementalComposition, repeats=True)


class XRFResult(MeasurementResult):
    """
    Section containing the result of an X-ray fluorescence measurement.
    """

    layer = SubSection(section_def=XRFLayer, repeats=True)

    date = Quantity(
        type=Datetime,
        a_eln=ELNAnnotation(component=ELNComponentEnum.DateTimeEditQuantity),
        description='Date of the measurement',
    )


class XRFSettings(ArchiveSection):
    """
    Section containing the settings for an XRF measurement.
    """

    xray_energy = Quantity(
        type=np.dtype(np.float64),
        unit=('eV'),
        a_eln=dict(component='NumberEditQuantity', defaultDisplayUnit='eV'),
    )

    current = Quantity(
        type=np.dtype(np.float64),
        unit=('uA'),
        a_eln=dict(component='NumberEditQuantity', defaultDisplayUnit='uA'),
    )

    spot_size = Quantity(
        type=np.dtype(np.float64),
        unit=('mm'),
        a_eln=dict(component='NumberEditQuantity', defaultDisplayUnit='mm'),
    )

    integration_time = Quantity(
        type=np.dtype(np.float64),
        unit=('s'),
        a_eln=dict(component='NumberEditQuantity', defaultDisplayUnit='s'),
    )

    element_line = Quantity(type=str, a_eln=dict(component='StringEditQuantity'))


class XRayFluorescence(Measurement):
    """
    Generic X-ray fluorescence measurement.
    """

    m_def = Section()
    method = Quantity(
        type=str,
        default='X-Ray Fluorescence (XRF)',
    )

    xrf_settings = SubSection(section_def=XRFSettings)

    results = Measurement.results.m_copy()
    results.section_def = XRFResult

    def normalize(self, archive: 'EntryArchive', logger: 'BoundLogger'):
        """
        The normalize function of the `XRayFluorescence` section.

        Args:
            archive (EntryArchive): The archive containing the section that is being
            normalized.
            logger (BoundLogger): A structlog logger.
        """
        if not archive.results:
            archive.results = Results()
        if not archive.results.properties:
            archive.results.properties = Properties()
        # if not archive.results.method:
        #     archive.results.method = Method(
        #         method_name='XRF',
        #         measurement=MeasurementMethod(
        #             xrf=XRFMethod()
        #         )
        #     )
        super().normalize(archive, logger)


class ELNXRayFluorescence(XRayFluorescence, EntryData):
    """
    Example section for how XRayFluorescence can be implemented with a general reader
    for some XRF file types.
    """

    m_def = Section(
        categories=[NOMADMeasurementsCategory],
        label='X-Ray Fluorescence (XRF)',
        a_eln=ELNAnnotation(
            lane_width='600px',
        ),
        a_template=dict(
            measurement_identifiers=dict(),
        ),
    )

    data_file = Quantity(
        type=str,
        description='Data file containing the xrf results',
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.FileEditQuantity,
        ),
    )

    measurement_identifiers = SubSection(
        section_def=ReadableIdentifiers,
    )

    def get_read_function(self) -> Callable:
        """
        Method for getting the correct read function for the current data file.

        Returns:
            Callable: The read function.
        """
        # TODO: Reader selection must be more specific
        if self.data_file.endswith('.txt'):
            return XRFreader.read_xrf_txt

    def write_xrf_data(
        self,
        xrf_dict: dict[str, Any],
        archive: 'EntryArchive',
        logger: 'BoundLogger',
    ) -> None:
        """
        Write method for populating the `ELNXRayFluorescence` section from a dict.

        Args:
            xrf_dict (dict[str, Any]): A dictionary with the XRF data.
            archive (EntryArchive): The archive containing the section.
            logger (BoundLogger): A structlog logger.
        """
        # Initialize results and samples lists
        list_of_results = []
        list_of_samples = []

        # write for each measurement in xrf_dict
        for data in xrf_dict.values():
            name = data.get('application', None)
            date = data.get('date', None)

            # create list of XRFLayers each with a list of XRFElementalCompositions
            list_of_XRFLayers = []
            for layer, content in data.get('layers', []).items():
                list_of_ElementalCompositions = []
                for element, attributes in content.get('elements', {}).items():
                    list_of_ElementalCompositions.append(
                        XRFElementalComposition(
                            element=element,
                            mass_fraction=attributes.get('mass_fraction'),
                            atomic_fraction=attributes.get('atomic_fraction'),
                            line=attributes.get('line'),
                            intensity_peak=attributes.get('intensity_peak'),
                            intensity_background=attributes.get('intensity_background'),
                            intensity_background_2=attributes.get(
                                'intensity_background_2'
                            ),
                        )
                    )
                list_of_XRFLayers.append(
                    XRFLayer(
                        name=layer,
                        thickness=content.get('thickness', None),
                        elements=list_of_ElementalCompositions,
                    )
                )

            sample = CompositeSystemReference(
                lab_id=data.get('sample_name', None),
            )
            # append new sample to samples list
            if sample not in list_of_samples:
                sample.normalize(archive, logger)
                list_of_samples.append(sample)

            # append new result to results list
            result = XRFResult(
                name=name,
                date=date,
                layer=list_of_XRFLayers,
            )
            result.normalize(archive, logger)
            list_of_results.append(result)

        xrf_settings = XRFSettings()
        xrf_settings.normalize(archive, logger)

        xrf = ELNXRayFluorescence(
            results=list_of_results,
            xrf_settings=xrf_settings,
            samples=list_of_samples,
        )
        merge_sections(self, xrf, logger)

    def normalize(self, archive: 'EntryArchive', logger: 'BoundLogger'):
        """
        The normalize function of the `ELNXRayFluorescence` section.

        Args:
            archive (EntryArchive): The archive containing the section that is being
            normalized.
            logger (BoundLogger): A structlog logger.
        """
        if self.data_file is not None:
            read_function = self.get_read_function()
            if read_function is None:
                if logger is not None:
                    logger.warn(
                        f'No compatible reader found for the file: "{self.data_file}".'
                    )
            else:
                with archive.m_context.raw_file(self.data_file) as file:
                    xrf_dict = read_function(file.name, logger)
                if xrf_dict:
                    self.write_xrf_data(xrf_dict, archive, logger)
                elif logger is not None:
                    logger.warn(f'No XRF data found in file: "{self.data_file}".')
        super().normalize(archive, logger)
        if not self.results:
            return


m_package.__init_metainfo__()
