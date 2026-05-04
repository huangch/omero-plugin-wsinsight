# -*- coding: utf-8 -*-
"""
OMECSV-to-OMERO ROI converter.

Runs as an OMERO.script: downloads an OMECSV file annotation attached to an
Image, then registers it as a label-image-backed ROI on that Image via
``ROI_Converter_NGFF.raster.director``.
"""

import csv
import gzip
import logging
import os
import shutil
import sys
import uuid

import omero.scripts as scripts
from omero.gateway import BlitzGateway
from omero.rtypes import rstring
from omero.util.temp_files import manager

from ROI_Converter_NGFF import raster

LOGGER = logging.getLogger(__name__)

# Workaround for csv field_size overflow on some platforms: try sys.maxsize
# and halve until it is accepted by the C long used internally by csv.
_max_int = sys.maxsize
while True:
    try:
        csv.field_size_limit(_max_int)
        break
    except OverflowError:
        _max_int = int(_max_int / 2)


def setup_logging(debug):
    level = logging.DEBUG if debug else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)-7s [%(name)16s] "
               "(%(thread)10s) %(message)s",
        stream=sys.stdout,
    )


def download_file_annotation(conn, annotation_id, directory):
    """Download a (gzipped) CSV FileAnnotation and return the unzipped path."""
    file_annotation = conn.getObject('FileAnnotation', annotation_id)

    file_id = str(uuid.uuid4())
    gzip_file_path = os.path.join(directory, 'omecsv-' + file_id + '.csv.gz')
    csv_file_path = os.path.join(directory, 'omecsv-' + file_id + '.csv')

    try:
        with open(gzip_file_path, 'wb') as f:
            for chunk in file_annotation.getFileInChunks():
                f.write(chunk)
    except Exception:
        LOGGER.error('Could not download the file annotation', exc_info=True)
        raise

    with gzip.open(gzip_file_path, 'rb') as f_in, \
            open(csv_file_path, 'wb') as f_out:
        shutil.copyfileobj(f_in, f_out)

    return csv_file_path


def run_omecsv_to_roi_conversion(
        csv_inputs, image_id, session_key, fill, debug, server='localhost'):
    """Convert each OMECSV file in ``csv_inputs`` to an OMERO label-image ROI.

    Args:
        csv_inputs: Mapping of ROI/table name -> path to OMECSV file.
        image_id: Target OMERO Image ID to register the ROI against.
        session_key: Active OMERO session key for registration.
        fill: If True, polygons are rasterized as filled regions.
        debug: Enable debug-level logging in the underlying converter.
        server: OMERO server hostname.
    """
    zarr_path = "/OMERO/NGFF/"

    for csv_file_name, csv_file_location in csv_inputs.items():
        args = {
            'input_file': csv_file_location,
            'directory': zarr_path,
            'output_filename': '',
            'width': None,
            'height': None,
            'tile_size': 2048,
            'no_fill': not fill,
            'register_to': image_id,
            'server': server,
            'port': 4064,
            'user': None,
            'password': None,
            'key': session_key,
            'series': '0',
            'label': None,
            'overwrite': False,
            'table': True,
            'name': csv_file_name,
            'column_name': 'polygon',
            'downsample_type': 'raster',  # choices: 'vector', 'raster'
            'num_objects': None,
            'no_clean': False,
            'max_procs': 8,
            'mode': 'local',  # choices: 'sqlite', 'postgres', 'local'
            'db': "postgresql://user:@localhost/table",
            'debug': debug,
            'server_directory': None,
            'disable_table_statistics': False,
            'table_name': csv_file_name,
            'offset_x': None,
            'offset_y': None,
        }

        LOGGER.info("Running raster.director with args: %s", args)
        raster.director(args)

    return "Done"


def run_as_omero_script():
    object_types = [rstring("Image")]
    client = scripts.client(
        'OMECSV_To_OMERO',
        """Converts an OMECSV file to a label image for annotations and
        detections. Label images can be viewed in PathViewer.""",
        scripts.String(
            "Data_Type",
            optional=False,
            grouping="1",
            description="Choose Image.",
            values=object_types, default="Image",
        ),
        scripts.List(
            "IDs",
            optional=False,
            grouping="2",
            description="Image ID",
        ),
        scripts.Long(
            "File_Annotation",
            optional=False,
            grouping="3",
            description="OMECSV file"),
        scripts.String(
            "Annotation_Name",
            optional=False,
            grouping="4",
            description="Annotation Name"),
        scripts.Bool(
            "Filled_Objects",
            optional=False,
            grouping="5",
            default=True,
            description="Fill in the ROI"),
        scripts.Bool(
            "Debug",
            optional=False,
            grouping="6",
            description="Debug mode"),
        version="0.1.0",
        authors=["Muhanad Zahra, Emil Rozbicki, Chao Hui Huang"],
        institutions=["Glencoe Software Inc., Pfizer Inc."],
        contact="support@glencoesoftware.com, chao-hui.huang@pfizer.com",
    )
    try:
        script_params = client.getInputs(unwrap=True)
        session = client.getSessionId()
        conn = BlitzGateway(client_obj=client)
        setup_logging(script_params["Debug"])

        omecsv_file = download_file_annotation(
            conn, script_params["File_Annotation"], manager.gettempdir())

        status = run_omecsv_to_roi_conversion(
            {script_params["Annotation_Name"]: omecsv_file},
            script_params["IDs"][0],
            session,
            fill=script_params["Filled_Objects"],
            debug=script_params["Debug"],
        )
        client.setOutput("Message", rstring(status))
    finally:
        client.closeSession()


if __name__ == '__main__':
    run_as_omero_script()
