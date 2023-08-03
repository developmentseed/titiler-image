"""Reader with GCPS support."""

import warnings
import xml.etree.ElementTree as ET
from typing import List, Optional, Union

import attr
import rasterio
from rasterio._path import _parse_path
from rasterio.control import GroundControlPoint
from rasterio.crs import CRS
from rasterio.dtypes import _gdal_typename
from rasterio.enums import MaskFlags
from rasterio.io import DatasetReader
from rasterio.transform import from_gcps
from rasterio.vrt import WarpedVRT
from rio_tiler import io
from rio_tiler.constants import WGS84_CRS
from rio_tiler.errors import NoOverviewWarning
from rio_tiler.utils import has_alpha_band


@attr.s
class Reader(io.Reader):
    """GCPS + Image Reader"""

    gcps: Optional[List[GroundControlPoint]] = attr.ib(default=None)
    gcps_crs: Optional[CRS] = attr.ib(default=WGS84_CRS)
    gcps_order: Optional[int] = attr.ib(default=None)

    cutline: Optional[str] = attr.ib(default=None)

    dataset: Union[DatasetReader, WarpedVRT] = attr.ib(init=False)

    def __attrs_post_init__(self):
        """Define _kwargs, open dataset and get info."""
        dataset = self._ctx_stack.enter_context(rasterio.open(self.input))

        # when external GCPS we create a VRT
        if self.gcps:
            vrt_xml = vrt_doc(dataset, gcps=self.gcps, gcps_crs=self.gcps_crs)
            dataset = self._ctx_stack.enter_context(rasterio.open(vrt_xml))

        vrt_options = {}

        # Options 1: GCPS (internal or external)
        if dataset.gcps[0]:
            vrt_options.update(
                {
                    "src_crs": dataset.gcps[1],
                    "src_transform": from_gcps(dataset.gcps[0]),
                }
            )
            if self.gcps_order is not None:
                vrt_options.update({"max_gcp_order": self.gcps_order})

        # Option 2: Cutline
        if self.cutline:
            vrt_options.update({"cutline": self.cutline})

        if vrt_options:
            vrt_options.update({"add_alpha": True})
            if dataset.nodata is not None:
                vrt_options.update(
                    {
                        "nodata": dataset.nodata,
                        "add_alpha": False,
                        "src_nodata": dataset.nodata,
                    }
                )

            elif has_alpha_band(dataset):
                vrt_options.update({"add_alpha": False})

            self.dataset = self._ctx_stack.enter_context(
                WarpedVRT(dataset, **vrt_options)
            )

        else:
            self.dataset = dataset

        self.bounds = tuple(self.dataset.bounds)
        self.crs = self.dataset.crs

        if self.colormap is None:
            self._get_colormap()

        if min(
            self.dataset.width, self.dataset.height
        ) > 512 and not self.dataset.overviews(1):
            warnings.warn(
                "The dataset has no Overviews. rio-tiler performances might be impacted.",
                NoOverviewWarning,
            )


def vrt_doc(  # noqa: C901
    src_dataset,
    gcps: Optional[List[GroundControlPoint]] = None,
    gcps_crs: Optional[CRS] = WGS84_CRS,
):
    """Make a VRT XML document.

    Adapted from rasterio.vrt._boundless_vrt_doc function
    """
    vrtdataset = ET.Element("VRTDataset")
    vrtdataset.attrib["rasterYSize"] = str(src_dataset.height)
    vrtdataset.attrib["rasterXSize"] = str(src_dataset.width)

    tags = src_dataset.tags()
    if tags:
        metadata = ET.SubElement(vrtdataset, "Metadata")
        for key, value in tags.items():
            v = ET.SubElement(metadata, "MDI")
            v.attrib["Key"] = key
            v.text = str(value)

    im_tags = src_dataset.tags(ns="IMAGE_STRUCTURE")
    if im_tags:
        metadata = ET.SubElement(vrtdataset, "Metadata")
        for key, value in im_tags.items():
            if key == "LAYOUT" and value == "COG":
                continue
            v = ET.SubElement(metadata, "MDI")
            v.attrib["Key"] = key
            v.text = str(value)

    if src_dataset.crs:
        srs = ET.SubElement(vrtdataset, "SRS")
        srs.text = src_dataset.crs.wkt if src_dataset.crs else ""
        geotransform = ET.SubElement(vrtdataset, "GeoTransform")
        geotransform.text = ",".join([str(v) for v in src_dataset.transform.to_gdal()])

    nodata_value = src_dataset.nodata

    if gcps:
        gcp_list = ET.SubElement(vrtdataset, "GCPList")
        gcp_list.attrib["Projection"] = str(gcps_crs)
        for gcp in gcps:
            g = ET.SubElement(gcp_list, "GCP")
            g.attrib["Id"] = gcp.id
            g.attrib["Pixel"] = str(gcp.col)
            g.attrib["Line"] = str(gcp.row)
            g.attrib["X"] = str(gcp.x)
            g.attrib["Y"] = str(gcp.y)

    for bidx, ci, block_shape, dtype in zip(
        src_dataset.indexes,
        src_dataset.colorinterp,
        src_dataset.block_shapes,
        src_dataset.dtypes,
    ):
        vrtrasterband = ET.SubElement(vrtdataset, "VRTRasterBand")
        vrtrasterband.attrib["dataType"] = _gdal_typename(dtype)
        vrtrasterband.attrib["band"] = str(bidx)

        if nodata_value is not None:
            nodata = ET.SubElement(vrtrasterband, "NoDataValue")
            nodata.text = str(nodata_value)

        colorinterp = ET.SubElement(vrtrasterband, "ColorInterp")
        colorinterp.text = ci.name.capitalize()

        source = ET.SubElement(vrtrasterband, "SimpleSource")
        sourcefilename = ET.SubElement(source, "SourceFilename")
        sourcefilename.attrib["relativeToVRT"] = "0"
        sourcefilename.text = _parse_path(src_dataset.name).as_vsi()
        sourceband = ET.SubElement(source, "SourceBand")
        sourceband.text = str(bidx)
        sourceproperties = ET.SubElement(source, "SourceProperties")
        sourceproperties.attrib["RasterXSize"] = str(src_dataset.width)
        sourceproperties.attrib["RasterYSize"] = str(src_dataset.height)
        sourceproperties.attrib["dataType"] = _gdal_typename(dtype)
        sourceproperties.attrib["BlockYSize"] = str(block_shape[0])
        sourceproperties.attrib["BlockXSize"] = str(block_shape[1])
        srcrect = ET.SubElement(source, "SrcRect")
        srcrect.attrib["xOff"] = "0"
        srcrect.attrib["yOff"] = "0"
        srcrect.attrib["xSize"] = str(src_dataset.width)
        srcrect.attrib["ySize"] = str(src_dataset.height)
        dstrect = ET.SubElement(source, "DstRect")
        dstrect.attrib["xOff"] = "0"
        dstrect.attrib["yOff"] = "0"
        dstrect.attrib["xSize"] = str(src_dataset.width)
        dstrect.attrib["ySize"] = str(src_dataset.height)

        if src_dataset.options is not None:
            openoptions = ET.SubElement(source, "OpenOptions")
            for ookey, oovalue in src_dataset.options.items():
                ooi = ET.SubElement(openoptions, "OOI")
                ooi.attrib["key"] = str(ookey)
                ooi.text = str(oovalue)

        if nodata_value is not None:
            nodata = ET.SubElement(source, "NODATA")
            nodata.text = str(nodata_value)

    if all(MaskFlags.per_dataset in flags for flags in src_dataset.mask_flag_enums):
        maskband = ET.SubElement(vrtdataset, "MaskBand")
        vrtrasterband = ET.SubElement(maskband, "VRTRasterBand")
        vrtrasterband.attrib["dataType"] = "Byte"

        source = ET.SubElement(vrtrasterband, "SimpleSource")
        sourcefilename = ET.SubElement(source, "SourceFilename")
        sourcefilename.attrib["relativeToVRT"] = "0"
        sourcefilename.attrib["shared"] = "0"
        sourcefilename.text = _parse_path(src_dataset.name).as_vsi()

        sourceband = ET.SubElement(source, "SourceBand")
        sourceband.text = "mask,1"
        sourceproperties = ET.SubElement(source, "SourceProperties")
        sourceproperties.attrib["RasterXSize"] = str(src_dataset.width)
        sourceproperties.attrib["RasterYSize"] = str(src_dataset.height)
        sourceproperties.attrib["dataType"] = "Byte"
        sourceproperties.attrib["BlockYSize"] = str(block_shape[0])
        sourceproperties.attrib["BlockXSize"] = str(block_shape[1])
        srcrect = ET.SubElement(source, "SrcRect")
        srcrect.attrib["xOff"] = "0"
        srcrect.attrib["yOff"] = "0"
        srcrect.attrib["xSize"] = str(src_dataset.width)
        srcrect.attrib["ySize"] = str(src_dataset.height)
        dstrect = ET.SubElement(source, "DstRect")
        dstrect.attrib["xOff"] = "0"
        dstrect.attrib["yOff"] = "0"
        dstrect.attrib["xSize"] = str(src_dataset.width)
        dstrect.attrib["ySize"] = str(src_dataset.height)

    return ET.tostring(vrtdataset).decode("ascii")
