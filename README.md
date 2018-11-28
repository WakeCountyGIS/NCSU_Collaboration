## Requirements:
    Python 3.6
    Libraries needed: (exact version only necessary for Rasterio)
        Rasterio 1.09
        Fiona 1.7
        Numpy 1.15
### PSEUDO-CODE:
    SETUP OUTPUT FOLDERS
    NDVI
        - MAX_NDVI
    CHANGE
    FOR FILE IN DATA FOLDER:
        UNTAR INTO FOLDER WITH SAME NAME AS TAR
        PROCESS NDVI AND PLACE IN OUTPUT NDVI FOLDER (NAMING NDVI_YYYYMMDD.TIF)
    CREATE ARRAY OF YEAR SETS:
    FOR YEAR IN YEARS:
        PROCESS INDIVIDUAL YEAR MAX_NDVI INTO MAX_NDVI FOLDER (NAMING MAX_NDVI_YYYY.TIF)
    CREATE ORDERED LIST OF MAX_NDVI RASTERS
    FOR EACH YEAR PAIR:
        SUBTRACT OLD FROM NEW
        ALL VALUES BELOW -0.25 --> 1
        ALL OTHER VALUES --> 0
        SET NODATA VALUE WHEN WRITING OUT RASTER TO 0
        WRITE OUT FINAL RASTERS TO CHANGE FOLDER

####Assumptions:
    1 - folder structure is the same for all data collected from Earth Explorer for Analysis Ready Surface Reflectance
        data.
        file/folder format - LXSS_US_HHHVVV_YYYYMMDD_yyyymmdd_CCC_VVV_PRODUCT.tar --> ex. LT05_CU_027011_20000908_20170918_C01_V01_SR.tar
        L - landsat
        X - Sensor (“T” = TM, “E” = ETM+, “C” = OLI/TIRS Combined, “O” = OLI-only, “T” = TIRS-only)
        SS - Satellite (“04” = Landsat 4, “05” = Landsat 5, “07” = Landsat 7, “08” = Landsat 8)
        US - Regional grid of the U.S. (“CU” = CONUS, “AK” = Alaska, “HI” = Hawaii)
        HHH	- Horizontal tile number
        VVV	- Vertical tile number
        YYYYMMDD - Acquisition year (YYYY) month (MM) day (DD)
        yyyymmdd - Production year (yyyy) month (mm) day (dd)
        CCC	- Level-1 Collection number (“C01,” “C02”)
        VVV	- ARD Version number (“V01,” “V02”)
        PRODUCT	- Data product (“TA” = top of atmosphere reflectance, “BT” = brightness temperature, “SR” = surface reflectance, “ST” = land surface temperature, “QA” = quality assessment)
    2 - the satellite(SS) and date (YYYYMMDD) should allow the code to process each year together and use appropriate bands for LS5 and LS8
    3 - by using data from throughout the year any cloud coverage will be eliminated without a mask by determining the MAX NDVI value for a
        given year.
    4 - Data used are from 1995 - 2015, March - October, with cloud cover and cloud shadow calculated below 30%
    input: single folder of .TAR files containing all data
    output: folder of NDVI rasters for each year, folder of change rasters for each time step 95-96, 96-97, and so on
    