# Land Parcel Automater

Internal tool for automating land parcel data processing.

### Github Secrets

Repository Secrets
secrets.DOCKERHUB_USERNAME
secrets.DOCKERHUB_TOKEN
secrets.AZURE_CREDENTIALS
secrets.MONGO_CONNECTION_STRING 
secrets.AZURE_CONNECTION_STRING
secrets.AZURE_STATIC_WEB_APPS_API_TOKEN
secrets.AZURE_CLIENT_ID

Repository Variables
vars.NAME
vars.PUBLIC_API_BASE_URL
vars.PUBLIC_MAPTILER_API_KEY
vars.PUBLIC_APP_BASE_PATH
###

apps\web\src\data\epsg\Indiana.json
```json
{
    "name": "String",
    "unit": "String",
    "proj4": "String",
    "_id": Number
  },
```

apps\web\src\data\gis\Indiana.json
```json
{
    "county": "String",
    "url": "String"
  },
  ```
### Useful links
- [Create a hover effect](https://docs.maptiler.com/sdk-js/examples/hover-styles/)
- [Restrict map panning to an area](https://docs.maptiler.com/sdk-js/examples/restrict-bounds/)
- [Show polygon information on click](https://docs.maptiler.com/sdk-js/examples/polygon-popup-on-click/)
- [Show polygon data from GeoJSON on the map](https://docs.maptiler.com/sdk-js/examples/geojson-polygon/)
- [Polygon layer (polygon helper)](https://docs.maptiler.com/sdk-js/examples/helper-polygon-minimal/)
- [Microsoft Entra ID]()
- [Indiana County Boundaries](https://hub.arcgis.com/maps/INMap::county-boundaries-of-indiana-2023)
- [2024 Countywide Shapefiles](https://dataharvest.gio.in.gov/pages/data-access)