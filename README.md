# omero-plugin-wsinsight

OMERO.script that imports WSInsight OME-CSV outputs as label-image-backed ROIs on an OMERO Image.

It downloads an OME-CSV file annotation attached to a target Image, then registers the contained masks/polygons as ROIs via `ROI_Converter_NGFF.raster.director`. Adapted from publicly published Glencoe Software OMERO.script examples.

## Requirements

- OMERO.server with scripting enabled
- `ROI_Converter_NGFF` available on the script's Python path
- Standard `omero-py` client modules (`omero.scripts`, `omero.gateway`, `omero.rtypes`, `omero.util.temp_files`)

## Install

Drop `omecsv2omero.py` into your OMERO scripts directory (typically `OMERO.server/lib/scripts/omero/<group>/`) so it shows up under **Scripts** in OMERO.web / Insight.

## License

Apache 2.0 — see [`LICENSE`](LICENSE).
