#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""

Name:
    modis数据处理

Description:
    modis数据读取、去除异常值、投影转换、裁剪和栅格求和（蒸散发数据、NPP、GPP）

Parameters
    参数1: modis影像 #input,infile,*.hdf
    参数2: 输出影像 #output,outfile,*.tif

"""

import os
import os.path
import sys
from osgeo import gdal, ogr
from osgeo import gdal_array
import time
import numpy as np

# ignore warning
np.seterr(divide='ignore', invalid='ignore')
gdal.SetConfigOption('CPL_LOG', 'NUL')
gdal.UseExceptions()
ogr.UseExceptions()

start = time.time()
driver_img = gdal.GetDriverByName('GTiff')
driver_shp = ogr.GetDriverByName('ESRI Shapefile')


# 读栅格文件
def read_img(filename):
    dataset = gdal.Open(filename)  # 打开文件
    print(dataset)
    im_width = dataset.RasterXSize  # 栅格矩阵的列数
    print(im_width)
    im_height = dataset.RasterYSize  # 栅格矩阵的行数
    im_bands = dataset.RasterCount  # 波段数

    im_geotrans = dataset.GetGeoTransform()  # 仿射矩阵，左上角像素的大地坐标和像素分辨率
    im_proj = dataset.GetProjection()  # 地图投影信息，字符串表示
    im_data = dataset.ReadAsArray(0, 0, im_width, im_height)  # 将数据写成数组，对应栅格矩阵

    del dataset
    return im_height, im_width, im_geotrans, im_proj, im_data

# 写栅格文件
def write_img(filename, im_proj, im_geotrans, im_data):
    # 判断栅格数据的数据类型
    if 'int8' in im_data.dtype.name:
        datatype = gdal.GDT_Byte
    elif 'int16' in im_data.dtype.name:
        datatype = gdal.GDT_UInt16
    else:
        datatype = gdal.GDT_Float32
    # 判断数组维数
    if len(im_data.shape) == 3:
        im_bands, im_height, im_width = im_data.shape
    else:
        im_bands, (im_height, im_width) = 1, im_data.shape
    # 创建文件
    driver = gdal.GetDriverByName('GTiff')  # 数据类型必须有
    dataset = driver.Create(filename, im_width, im_height, im_bands, datatype)
    dataset.SetGeoTransform(im_geotrans)  # 写入仿射变换参数
    dataset.SetProjection(im_proj)  # 写入投影
    if im_bands == 1:
        dataset.GetRasterBand(1).WriteArray(im_data)
    else:
        for i in range(im_bands):
            dataset.GetRasterBand(i + 1).WriteArray(im_data[i])
    del dataset


# 读取hdf中的波段，保存为tif
def readHdfWithGeo(hdfFloder, saveFloder, refer_data_file):
    hdfNameList = os.listdir(hdfFloder)
    print('文件个数：', len(hdfNameList))
    refer_data = gdal.Open(refer_data_file)
    proj = refer_data.GetProjectionRef()
    im_geotrans = refer_data.GetGeoTransform()

    # 遍历文件名列表中所有文件
    for i in range(len(hdfNameList)):
        dirname, basename = os.path.split(hdfNameList[i])  # 获取文件名后缀
        filename, txt = os.path.splitext(basename)
        hdfPath = hdfFloder + os.sep + hdfNameList[i]  # os.sep: 跨平台的文件路径分隔符
        datasets = gdal.Open(hdfPath)
        sus = datasets.GetSubDatasets()
        et_rows, et_columns, et_geotrans, et_proj, et_array = read_img(sus[1][0])
        print('产品子数据集个数为：', len(sus))
        et_array = et_array.astype(np.float32)
        et_array[np.where((et_array < -32761) | (et_array > 32761))] = 0  # <-32767以及>32700设为空值，不参与计算
        Scale_Factor = 0.0001
        et_array = et_array * Scale_Factor
        write_img(saveFloder + os.sep + filename + '_pro.tif',
                         proj, im_geotrans, et_array)


# 栅格裁剪
def cut_img(tifFloder, saveFloder, shpFile):
    tifNameList = os.listdir(tifFloder)
    for i in range(len(tifNameList)):
        filename, txt = os.path.splitext(tifNameList[i])
        if txt == '.tif':
            tifPath = tifFloder + os.sep + tifNameList[i]
            outName = saveFloder + os.sep + filename + '_cut' + txt
            cut_img = gdal.Warp(outName, tifPath,
                               cutlineDSName=shpFile,
                               cropToCutline=True)
            del cut_img
            print('{filename} deal end '.format(filename=outName))


# 栅格批量求和
def sum_img(tifFloder, saveFloder, refer_data_file):
    rows, cols, geotrans, proj, data_array = read_img(refer_data_file)
    filenames = os.listdir(tifFloder)
    nd_arr = np.zeros((len(filenames), rows, cols))

    i = 0
    for filename in filenames:
        if os.path.splitext(filename)[1] == '.tif':
            dataset = gdal.Open(tifFloder + os.sep + filename)
            array = dataset.ReadAsArray()
            nd_arr[i] = array
            del array
            i += 1

    sum_arr = np.sum(nd_arr, axis=0)
    write_img(saveFloder + os.sep + filename + '_sum.tif',
              proj, geotrans, sum_arr)

    
if __name__ == "__main__":
    start = time.time()
    # 参考影像和矢量
    refer_data_file = r'D:\Data\data_modis\data_results\MOD17A2\MOD17A2_clip\MOD17A2H.A2021361.h27v05.006.2022005050243_pro_cut.tif'
    shpFile = r'D:\Data\data_modis\data_reference\hebi_pro.shp'

    # 文件路径
    hdfFloder = r'D:\Data\data_modis\data_ori\MOD173AHGFv061'
    proFloder = r'D:\Data\DEM\dem_500m'
    clipFloder = r'D:\Data\data_modis\data_results\MOD17A2\MOD17A2_clip'
    saveFloder = r'D:\Data\data_modis\data_results\MOD17A2\sum_img'

    # 执行函数
    # readHdfWithGeo(hdfFloder, proFloder, refer_data_file)
    # cut_img(proFloder, clipFloder, shpFile)
    sum_img(clipFloder, saveFloder, refer_data_file)
    end = time.time()
    print('deal spend: {s} s'.format(s=end - start))








