# -*- coding: utf-8 -*-
"""
Created on Wed Sep  4 10:01:11 2024

@author: dell
"""

import os
import xarray as xr
import pandas as pd
import numpy as np
from tqdm import tqdm
import netCDF4 as nc
from datetime import datetime, timedelta
from scipy import interpolate
import time
import math
import re
import argparse

parser = argparse.ArgumentParser()
parser.add_argument("--start_date_str", type=str, required=True)
parser.add_argument("--predict_days", type=int, required=True)
parser.add_argument("--domain", type=str, required=True)
parser.add_argument("--area", type=str, required=True)
parser.add_argument("--pollen_emiss_path", type=str, required=True)
parser.add_argument("--meic_save_dir", type=str, required=True)
parser.add_argument("--meic_poll_save_dir", type=str, required=True)
args = parser.parse_args()

start_date_str = args.start_date_str     ####20240801
predict_days   = args.predict_days       ####3
domain         = args.domain
area           = args.area
pollen_emiss_path  = args.pollen_emiss_path
meic_save_dir      = args.meic_save_dir
meic_poll_save_dir = args.meic_poll_save_dir

# 将字符串转换为日期对象
date_obj           = datetime.strptime(start_date_str, "%Y%m%d")
poll_flux_date     = (date_obj - timedelta(days=1)).strftime("%Y%m%d")    # 生成的pollen_flux文件提前一天  以20240801为基准，这里为20240731
meic_combined_date = (date_obj - timedelta(days=2)).strftime("%Y%m%d")    # 生成的pollen_flux文件提前两天  以20240801为基准，这里为20240730
print("poll_flux_date is:", poll_flux_date)
print("meic_combined_date is:", meic_combined_date)
# 将结果转换回字符串格式
run_days = predict_days + 2


def pollen_distribution(file_pollen, XLAT, XLONG, start_day_nc, end_day_nc, spec_name):
    #####总花粉浓度
    pollen = nc.Dataset(file_pollen, 'r')
    poll_data = pollen.variables[spec_name][:]
    poll_time = pollen.variables['times_pre'][:]
    xlat = pollen.variables['xlat'][:]     #一维
    xlon = pollen.variables['xlon'][:]
    units = pollen.variables['times_pre'].units
    calendar = pollen.variables['times_pre'].calendar
    # 使用 netCDF4 的 num2date 将 poll_time 转换为日期
    poll_dates = nc.num2date(poll_time, units=units, calendar=calendar)

    # ###找到 start_time 和 end_time 对应的 day_index     ####pollen_flux_pre中的时间都是以0h0min0s结束的,只用对齐year mon day即可
    # 构造 poll_dates 中只包含年月日的 datetime 列表
    poll_dates_dt = [datetime(d.year, d.month, d.day) for d in poll_dates]
    start_day_index = poll_dates_dt.index(start_day_nc)
    end_day_index = poll_dates_dt.index(end_day_nc)
    # print(start_day_index, end_day_index)   ##0, 4
    # 为每个小时分配花粉排放数据
    hourly_pollen_data = []
    for day_index in range(start_day_index, end_day_index+1):
        # 提取该天的花粉数据
        daily_pollen = poll_data[day_index, :, :]  # 获取对应天的数据
        last_hour = 23
        # 将该天的花粉数据按时间分布系数分配到对应的小时
        for hour_index in range(0, last_hour + 1):
            hourly_pollen = daily_pollen * pollen_time_distribution[hour_index]
            hourly_pollen_data.append(hourly_pollen)
    hourly_pollen_data = np.array(hourly_pollen_data)

    xlon, xlat = np.meshgrid(xlon, xlat)
    hourly_pollen_data_wrf = np.zeros((hourly_pollen_data.shape[0], XLAT.shape[0], XLAT.shape[1]))
    for i in tqdm(range(hourly_pollen_data.shape[0])):
        hourly_pollen_data_wrf[i] = bilinear_interpolation(xlon.flatten(), xlat.flatten(), hourly_pollen_data[i].flatten(), XLONG, XLAT)

    # 获取 hourly_pollen_data_wrf 的维度信息
    time_dim, lat_dim, lon_dim = hourly_pollen_data_wrf.shape
    # 初始化四维数组，分别是 (time, lev, lat, lon)
    hourly_pollen_data_wrf_4d = np.zeros((time_dim, len(lev), lat_dim, lon_dim))
    # 对每个时间步的数据进行扩展
    for t in range(time_dim):
        for l in range(len(lev)):
            hourly_pollen_data_wrf_4d[t, l, :, :] = hourly_pollen_data_wrf[t, :, :] * lev[l]

    ## 10^3 Grain m-3 h-1 to ug m-3 s-1
    ## R = 35um  density = 1200kg m-3
    hourly_pollen_data_wrf_4d = hourly_pollen_data_wrf_4d * 10**3 * (4/3) * math.pi * (35/2)**3 * 1.2 * 10**-6 / 3600   ##3600 means hour to sec
    del hourly_pollen_data_wrf, hourly_pollen_data, hourly_pollen, poll_data, poll_dates
    return hourly_pollen_data_wrf_4d

def bilinear_interpolation(x, y, z, xi, yi):
    # 进行插值
    result = interpolate.griddata((x, y), z, (xi, yi), method='linear')
    # 将NaN值替换为0
    result[np.isnan(result)] = 0
    return result

# ************************************************************************************************
##花粉排放每日时间分布  0-23  此处为世界时，模式模拟从12点-12点，即北京时间20点-20点，那么第一个时间对应北京时间20点
pollen_time_distribution = [0.1, 0.1, 0.1, 0.1,                        ###20点, 21点, 22点, 23点   北京时间
                            0.1, 0.1, 0.1, 0.1, 0.1, 0.2, 4, 4,        ###0-7点   北京时间
                            3.3, 3, 2.5, 2,                            ###8-11点   北京时间
                            1.5, 1, 0.5, 0.4, 0.3, 0.2, 0.1, 0.1       ###12-19点   北京时间
                            ]
pollen_time_distribution = np.array(pollen_time_distribution)
pollen_time_distribution /= np.sum(pollen_time_distribution)  # 归一化
lev = [1.000, 0.000, 0.000, 0.000, 0.000, 0.000, 0.000, 0.000]  #, 0.000, 0.000, 0.000]  ##修改成6层



# 计算时间范围
start_time = datetime.strptime(meic_combined_date, "%Y%m%d").replace(hour=12, minute=0, second=0)
end_time = (start_time + timedelta(days=run_days)).replace(hour=11, minute=0, second=0)
print(start_time, end_time)
year = start_time.year
mon  = start_time.month
day  = start_time.day

pollen_file = os.path.join(pollen_emiss_path, f'{area}_emission_{poll_flux_date}_pre{predict_days}.nc')
# print(pollen_file)

combined_file = os.path.join(meic_save_dir, f'combined_wrfchemi_{domain}_{year}_{mon:02d}_{day:02d}.nc')
# combined_file = meic_save_dir + f'combined_wrfchemi_{domain}_2024_{mon:02d}_{day:02d}.nc'
data = nc.Dataset(combined_file, 'r')
var_all = list(data.variables.keys())
XLAT = data.variables['XLAT'][:]   # 二维
XLONG = data.variables['XLONG'][:]
times = data.variables['Times'][:]
# print(times)
combined_times = []
for t in times:
    # 将字符数组转换为字符串
    time_str = ''.join([c.decode('utf-8') if isinstance(c, bytes) else c for c in t]).strip()
    combined_times.append(time_str)
# print(combined_times)
# 修改年份为目标年份
# combined_times_new = [t.replace('2024', str(year), 1) for t in combined_times]
# print(combined_times_2025)

# 生成每小时的时间序列
time_delta = timedelta(hours=1)
time_list = []
current_time = start_time
while current_time <= end_time:
    time_list.append(current_time)
    current_time += time_delta

# 生成新文件的时间字符串列表
time_strings = [t.strftime('%Y-%m-%d_%H:%M:%S') for t in time_list]
# print(time_strings)

# 在组合文件中查找匹配的时间索引
time_indices = []
for ts in time_strings:
    try:
        # 查找匹配的时间位置
        idx = combined_times.index(ts)
        time_indices.append(idx)
    except ValueError:
        print(f"警告: 时间 {ts} 在组合文件中未找到，将使用0填充")
        # 如果找不到匹配项，使用-1标记（后续处理）
        time_indices.append(-1)

poll_start_day = poll_flux_date
start_day_nc = datetime.strptime(poll_start_day, "%Y%m%d")   # 字符串转 datetime
poll_end_day   = (date_obj + timedelta(days=predict_days)).strftime("%Y%m%d")
end_day_nc = datetime.strptime(poll_end_day, "%Y%m%d")
# print(start_day_nc, end_day_nc)
# 假设pollen_distribution函数已定义
hourly_pollen_data_wrf_4d_tot = pollen_distribution(pollen_file, XLAT, XLONG, start_day_nc, end_day_nc, 'TotPC_pollen_flux_pre')
hourly_pollen_data_wrf_4d_art = pollen_distribution(pollen_file, XLAT, XLONG, start_day_nc, end_day_nc, 'Artemisia_pollen_flux_pre')
hourly_pollen_data_wrf_4d_che = pollen_distribution(pollen_file, XLAT, XLONG, start_day_nc, end_day_nc, 'Chenopods_pollen_flux_pre')

# 创建新文件
os.makedirs(meic_poll_save_dir, exist_ok=True)
new_file = os.path.join(meic_poll_save_dir, f'wrfchemi_{domain}_{year}-{mon:02d}-{day:02d}_12_00_00.nc')
if os.path.exists(new_file):
    os.remove(new_file)

ncfile = nc.Dataset(new_file, 'a', format='NETCDF4_CLASSIC')
# 创建维度
ncfile.createDimension('Time', len(time_list))
ncfile.createDimension("DateStrLen", 19)
ncfile.createDimension('emissions_zdim', hourly_pollen_data_wrf_4d_tot.shape[1])
ncfile.createDimension('south_north', hourly_pollen_data_wrf_4d_tot.shape[2])
ncfile.createDimension('west_east', hourly_pollen_data_wrf_4d_tot.shape[3])

# 设置全局属性
ncfile.setncattr("TITLE", "EMISSIONS for WRF-Chem")
ncfile.setncattr("MMINLU", "MODIFIED_IGBP_MODIS_NOAH")
ncfile.setncattr("NUM_LAND_CAT", 20)

# 创建 Times 变量，并写入时间数据
times_var = ncfile.createVariable("Times", 'c', ('Time', 'DateStrLen'))
times_var.setncattr('units', "secs since 1970-01-01 00:00:00")
# print(time_strings)
for i, time_str in enumerate(time_strings):
    # 确保字符串长度不超过19个字符
    char_array = np.array(list(time_str.ljust(19)[:19]), 'S1')
    times_var[i, :] = char_array

# print(var_all)
# print(data.variables['E_HC8'][:].shape)

required_emission_vars = [
    'E_CO', 'E_NH3', 'E_NO', 'E_NO2', 'E_SO2', 'E_ALD', 'E_CSL', 'E_ETH',
    'E_HC3', 'E_HC5', 'E_HC8', 'E_HCHO', 'E_ISO', 'E_KET', 'E_OL2',
    'E_OLI', 'E_OLT', 'E_ORA2', 'E_TOL', 'E_XYL', 'E_ECI', 'E_ECJ',
    'E_ORGI', 'E_ORGJ', 'E_PM25I', 'E_PM25J', 'E_PM_10', 'E_SO4I',
    'E_SO4J', 'E_NO3I', 'E_NO3J',
]

# 创建新的变量，并指定维度。MEIC 当前未计算的物种填零，保证 WRF-Chem 输入结构完整。
for spec in required_emission_vars:
    print(spec)
    if spec not in ['XLONG', 'XLAT', 'Times']:
        # 创建变量
        var = ncfile.createVariable(spec, 'f4', ('Time', 'emissions_zdim', 'south_north', 'west_east'))
        var.setncattr('description', 'EMISSIONS')
        if spec in ["E_PM25I","E_PM25J","E_SO4I","E_SO4J","E_NO3I","E_NO3J","E_ORGI","E_ORGJ","E_ECI","E_ECJ","E_PM_10"]:
            var.setncattr('units', "mol km^-2 hr^-1")
        else:
            var.setncattr('units', "ug^m-3 m^s-1")
        var.setncattr('coordinates', 'XLONG XLAT')
        var.setncattr('stagger', '')
        var.setncattr('MemoryOrder', 'XYZ')
        var.setncattr('FieldType', 104)

        # 关键修改：提取匹配时间段的数据
        if spec in data.variables and len(data.variables[spec].shape) == 4:  # 确认是4D变量
            # 创建空数组存放提取的数据
            selected_data = np.zeros((len(time_list),) + data.variables[spec].shape[1:])

            for i, idx in enumerate(time_indices):
                if idx >= 0:  # 有效索引
                    selected_data[i] = data.variables[spec][idx]
                else:  # 无效索引（时间点不存在）
                    selected_data[i] = 0  # 填充默认值
                    print(f"为变量 {spec} 在时间点 {time_strings[i]} 使用默认值0")

            var[:, :, :, :] = selected_data
        else:
            print(f"变量 {spec} 缺失或不是4维数组，使用零场")
            var[:, :, :, :] = np.zeros_like(hourly_pollen_data_wrf_4d_tot)

# 添加花粉变量
print('E_POLLEN')
var = ncfile.createVariable('E_POLLEN', 'f4', ('Time', 'emissions_zdim', 'south_north', 'west_east'))
var.setncattr('description', 'EMISSIONS')
var.setncattr('units', "ug m^-3 s^-1")
var.setncattr('coordinates', 'XLONG XLAT')
var.setncattr('stagger', '')
var.setncattr('MemoryOrder', 'XYZ')
var.setncattr('FieldType', 104)
var[:, :, :, :] = hourly_pollen_data_wrf_4d_tot
del hourly_pollen_data_wrf_4d_tot

print('E_POLLEN_Arte')
var = ncfile.createVariable('E_POLLEN_Arte', 'f4', ('Time', 'emissions_zdim', 'south_north', 'west_east'))
var.setncattr('description', 'EMISSIONS')
var.setncattr('units', "ug m^-3 s^-1")
var.setncattr('coordinates', 'XLONG XLAT')
var.setncattr('stagger', '')
var.setncattr('MemoryOrder', 'XYZ')
var.setncattr('FieldType', 104)
var[:, :, :, :] = hourly_pollen_data_wrf_4d_art
del hourly_pollen_data_wrf_4d_art

print('E_POLLEN_Chen')
var = ncfile.createVariable('E_POLLEN_Chen', 'f4', ('Time', 'emissions_zdim', 'south_north', 'west_east'))
var.setncattr('description', 'EMISSIONS')
var.setncattr('units', "ug m^-3 s^-1")
var.setncattr('coordinates', 'XLONG XLAT')
var.setncattr('stagger', '')
var.setncattr('MemoryOrder', 'XYZ')
var.setncattr('FieldType', 104)
var[:, :, :, :] = hourly_pollen_data_wrf_4d_che
del hourly_pollen_data_wrf_4d_che

# 添加坐标变量
print('XLAT')
var = ncfile.createVariable('XLAT', 'f4', ('south_north', 'west_east'))
var.setncattr('description', 'LATITUDE, SOUTH IS NEGATIVE')
var.setncattr('units', "degree north")
var.setncattr('MemoryOrder', 'XYZ')
var[:, :] = XLAT

print('XLONG')
var = ncfile.createVariable('XLONG', 'f4', ('south_north', 'west_east'))
var.setncattr('description', 'LONGITUDE, WEST IS NEGATIVE')
var.setncattr('units', "degree east")
var.setncattr('MemoryOrder', 'XYZ')
var[:, :] = XLONG

# 关闭文件
ncfile.close()
data.close()
print(f"成功创建文件: {new_file}")








