'''
PSEUDO-CODE
assumptions:
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
'''

import fiona
import rasterio
from rasterio.mask import mask
from rasterio.warp import calculate_default_transform, reproject, Resampling
import numpy
import os
import tarfile
import re
import glob
import errno

# Allow division by zero
numpy.seterr(divide='ignore', invalid='ignore')
dst_CRS = 'EPSG:2264'


def build_folders(directory):
    """
    simple function to build directory structure for code
    :param directory: string path to data folder
    :return: list of directories
    """
    output_NDVI = os.path.join(directory, 'NDVI')
    max_NDVI = os.path.join(output_NDVI, 'MAX_NDVI')
    change = os.path.join(directory, 'CHANGE')
    folders = [output_NDVI, max_NDVI, change]
    for folder in folders:
        if not os.path.exists(folder):
            try:
                os.mkdir(folder)
            except OSError as oserr:
                if oserr.errno != errno.EEXIST:
                    raise

    return folders


def reproj_raster(raster):
    # unused function, could be valuable if a different projection is prefered,
    # currently the data remain in the CRS downloaded from Earth Explorer
    """
    function to reporject a raster to state plane feet
    :param raster: raster to be projected
    :return: projected raster file path
    """
    path, file = os.path.split(raster)
    out_raster = os.path.join(path, file[:-4] + '.NC_SPF.tif')
    with rasterio.open(raster) as src:
        transform, width, height = calculate_default_transform(
            src.crs, dst_CRS, src.width, src.height, *src.bounds)
        kwargs = src.meta.copy()
        kwargs.update(
            crs=dst_CRS,
            transform=transform,
            width=width,
            height=height)
        with rasterio.open(out_raster, 'w', **kwargs) as dst:
            for i in range(1, src.count + 1):
                reproject(
                    source=rasterio.band(src, i),
                    destination=rasterio.band(dst, i),
                    src_transform=src.transform,
                    src_crs=src.crs,
                    dst_transform=transform,
                    dst_crs=dst_CRS,
                    resampling=Resampling.nearest)
    return out_raster


def process_VI(ref, abs, meta):
    """
    simple function to process the NIR and RED bands to NDVI, generalized enough to process other band
    combinations as well
    :param ref: reflectance band
    :param abs: absorption band
    :param meta: metadata about incoming rasters
    :return: vi array and updated metadata about created raster
    """
    # Calculate VI
    ndvi = (ref.astype(float) - abs.astype(float)) / (ref + abs)
    ndvi[ndvi > 1] = 1
    ndvi[ndvi < -1] = -1
    kwargs = meta
    # Update kwargs (change in data type)
    kwargs.update(
        driver='GTiff',
        dtype=rasterio.float32,
        count=1)
    return ndvi, kwargs


def calc_ndvi(working_dir, output_dir):
    """
    calculate NDVI value for Landsat 5 and Landsat 8 while only opening the bands needed from the archive
    :param working_dir:
    :param output_dir:
    :return: none
    """
    # create a list of only the tar files in the working directory
    satellite_files = glob.glob(working_dir + '\*.tar')
    # loop over tar files and calculate NDVI from appropriate bands
    for file in satellite_files:
        name, ext = os.path.splitext(os.path.basename(file))
        new_folder = os.path.join(working_dir, name)
        if not os.path.exists(new_folder):
            os.mkdir(new_folder)

        # set up regex to grab appropriate files for satellite and place unzip them for use
        parts = os.path.basename(file).split(sep='_')
        if parts[0] == 'LT05':
            bands_grep = re.compile(".*_(SRB3|SRB4)\.tif")
        if parts[0] == 'LC08':
            bands_grep = re.compile(".*_(SRB4|SRB5)\.tif")
        tar = tarfile.open(file)
        file_list = tar.getnames()
        bands = filter(lambda x: bands_grep.search(x), file_list)
        data = []
        for item in bands:
            tar.extract(item, path=new_folder)
            data.append(os.path.join(new_folder, item))

        # read in data for red(absorption) and nir(reflectance) bands
        with rasterio.open(data[0]) as src:
            absorb_band = src.read(1)
            meta = src.meta
        with rasterio.open(data[1]) as src:
            refl_band = src.read(1)

        # Calculate NDVI
        data, kwargs = process(refl_band, absorb_band, meta)
        ndvi_raster = os.path.join(output_dir, name + '_NDVI.tif')
        with rasterio.open(ndvi_raster, 'w', **kwargs) as dst:
            dst.write_band(1, data.astype(rasterio.float32))


def calc_max_ndvi(NDVI_folder, output_folder):
    """
    collect all NDVI rasters created for a given year and stack into N dimensional array, then
    write out the MAX value per pixel to a raster for that year
    :param NDVI_folder: folder containing NDVI rasters
    :param output_folder: output directory
    :return: none
    """
    ndvi_tifs = glob.glob(NDVI_folder + '\*.tif')
    # group tifs into year chunks using a dictionary key
    # for years and list of rasters for that year as values
    years = {}
    for tif in ndvi_tifs:
        file = os.path.basename(tif)
        year = file[15:19]
        if year not in years:
            years[year] = [tif]
        else:
            years[year].append(tif)

    # loop over each dictionary items and determine max value for each pixel
    for year, tifs in years.items():
        with rasterio.open(tifs[0]) as src:
            kwargs = src.meta
        kwargs.update(count=len(tifs))
        with rasterio.open(os.path.join(output_folder, 'stack.tif'.format(year)), 'w+', **kwargs) as stack:
            for id, tif in enumerate(tifs, start=1):
                with rasterio.open(tif) as src:
                    stack.write_band(id, src.read(1))
            stacked_rasters = stack.read()
            # determine max value per pixel and write to final raster
            kwargs.update(count=1)
            with rasterio.open(os.path.join(output_folder, 'NDVI_MAX_{}.tif'.format(year)), 'w', **kwargs) as dst:
                max_ndvi = numpy.max(stacked_rasters, axis=0)
                dst.write_band(1, max_ndvi)


def change_analysis(max_ndvi_dir, output_dir):
    """
    creates a list of all max ndvi tifs and processes them into change rasters
    :param max_ndvi_dir: directory where max NDVI rasters have been created
    :param output_dir: output directory
    :return:
    """
    # collect all MAX_NDVI rasters into a list and sort them in descending order
    max_ndvi_tifs = glob.glob(max_ndvi_dir + '\\NDVI_MAX_*.tif')
    sorted = max_ndvi_tifs.copy()
    sorted.reverse()
    # define a masking geometry of the county for clipping the final result
    with fiona.open(r"D:\BDA\data\Bulk Order 960972\wake_county_mask__.shp", "r") as shapefile:
        geoms = [feature["geometry"] for feature in shapefile]
        out_crs = shapefile.crs
    while len(sorted) != 1:
        tifs = sorted[-2:]
        year1 = tifs[0][-8:-4]
        year2 = tifs[1][-8:-4]
        change_raster = subtract(tifs[0], tifs[1], out_crs, output_dir)
        # clip the change raster to the county line and mask out water bodies and agricultural parcels
        with rasterio.open(change_raster) as src:
            out_img, out_trans = mask(src, geoms, crop=True)
            kwargs = src.meta.copy()
            kwargs.update(
                driver='GTiff',
                height=out_img.shape[1],
                width=out_img.shape[2],
                transform=out_trans
            )
        with rasterio.open(os.path.join(output_dir, 'CHANGE_{}_{}.tif'.format(year1, year2)), 'w', **kwargs) as dst:
            dst.write(out_img)

        sorted.pop()


def subtract(time_newer, time_later, out_crs, output_dir):
    """
    Subtract the older from the newer data and threshold values to 1 if below -0.25
    and 0 if anything else
    :param time_newer: raster representing the more recent data
    :param time_later: raster representing the older data
    :param out_crs: output coordinate reference system neeeded to set the output value
    :param output_dir: output directory
    :return:
    """
    change_temp = os.path.join(output_dir, 'temp.tif')
    with rasterio.open(time_newer) as src:
        newer = src.read(1)
        kwargs = src.meta
    with rasterio.open(time_later) as src:
        later = src.read(1)
    kwargs.update(
        count=1,
        dtype=rasterio.uint8,
        crs=out_crs,
        nodata=0
    )
    change = (newer.astype(float) - later.astype(float))
    change[change > -0.25] = 0
    change[change <= -0.25] = 1
    change = change.astype(rasterio.uint8)
    with rasterio.open(change_temp, 'w', **kwargs) as dst:
        dst.write_band(1, change)
    return change_temp


def run(working_dir):
    try:
        # set up output directories
        output_ndvi, max_ndvi, change = build_folders(working_dir)
        # do work
        calc_ndvi(working_dir, output_ndvi)
        calc_max_ndvi(output_ndvi, max_ndvi)
        change_analysis(max_ndvi, change)
    except Exception as e:
        print(e)


if __name__ == "__main__":
    working_dir = r'D:\BDA\data\Bulk Order 964143\U.S. Landsat 4-8 ARD'
    run(working_dir)

## placing the working directory of data downloaded from Earth Explorer as .tar files, the script
## will process all data into the CHANGE folder resulting in change pixels within the county
## excluding water bodies and agricultural lands.