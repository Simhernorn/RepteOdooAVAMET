# AVAMET

The module stores AVAMET weather observations and camera image slots. Image fields are intentionally empty in the demo data; the `webcam*_file` fields retain only the filenames from the export and do not imply that the image files are present.

The bundled demonstration CSV contains the 4,000 records included in the supplied export. Its source reports 4,397 matching results, so 397 records were not present in the export and are not recreated here.

Users can add observations from the readings form or import one JSON object per operation from **AVAMET → Importa JSON**. JSON keys use the export field names. Required fields are the observation timestamp, current temperature, humidity, pressure, wind speed, and accumulated rainfall. The maximum numeric change is configurable in **Settings → AVAMET** and defaults to 100% relative to the closest observation in time.
