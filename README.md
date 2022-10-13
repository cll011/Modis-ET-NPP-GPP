# Modis-ET-NPP-GPP


Name:
    modis数据处理

Description:
    modis数据读取、去除异常值、投影转换、裁剪和栅格求和（蒸散发数据、NPP、GPP）

Parameters
    参数1: modis影像 #input,infile,*.hdf
    参数2: 输出影像 #output,outfile,*.tif

read_img函数：读栅格文件，返回影像的im_height, im_width, im_geotrans, im_proj, im_data；

write_img函数：保存栅格文件；

readHdfWithGeo函数：读取hdf中的子数据集，并去除异常值，保存为tif；

cut_img函数：按照矢量进行裁剪；

sum_img函数：8天一期的栅格数据求和，得到一年的累积值。
