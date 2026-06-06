# -*- coding: utf-8 -*-
"""
Created on Sun Jul 26 23:35:24 2025

@author: dell
"""
import os
import pandas as pd
import xarray as xr
import numpy as np
from tqdm import tqdm
import netCDF4 as nc
from datetime import timedelta
import datetime
from scipy import interpolate
import re
from scipy.signal import find_peaks
from scipy.ndimage import uniform_filter1d
import math
from scipy.stats import norm
import argparse
import pickle

def senescence_rate(Ti, Tbase):
    return (Tbase - Ti) if Ti < Tbase else 0

def senescence_rate_sig(Ti, a, b):
    return 1 / (1 + math.exp(a * (Ti-b)))


def time_date(year, days_list):
    additional_dates = []
    for days in days_list:
        date_diff = timedelta(days=days)
        target_date = datetime.datetime(year, 1, 1) + date_diff
        additional_dates.append(target_date)
    date = np.array([nc.date2num(dt, units='days since 1900-01-01', calendar='standard') for dt in additional_dates])
    return date

# 双线性插值函数
def bilinear_interpolation_ij(x, y, x1, y1, x2, y2, Q11, Q21, Q12, Q22):
    # 计算 x 方向的插值
    R1 = Q11 + (x - x1) / (x2 - x1) * (Q21 - Q11)
    R2 = Q12 + (x - x1) / (x2 - x1) * (Q22 - Q12)
    # 计算 y 方向的插值
    P = R1 + (y - y1) / (y2 - y1) * (R2 - R1)
    return P

# 创建一个函数来执行双线性插值
def bilinear_interpolation(x, y, z, xi, yi):
    return interpolate.griddata((x, y), z, (xi, yi), method='linear')

def Reduce_scope(pft_lon, pft_lat, lon_lat):
    lon_pft = [value for value in pft_lon if lon_lat[0] <= value <= lon_lat[1]]
    lat_pft = [value for value in pft_lat if lon_lat[2] <= value <= lon_lat[3]]
    Wlon_ind = np.where(pft_lon == lon_pft[0])[0][0]
    Elon_ind = np.where(pft_lon == lon_pft[-1])[0][0]
    Slat_ind = np.where(pft_lat == lat_pft[0])[0][0]
    Nlat_ind = np.where(pft_lat == lat_pft[-1])[0][0]
    return lon_pft, lat_pft, Wlon_ind, Elon_ind, Slat_ind, Nlat_ind

parser = argparse.ArgumentParser()
parser.add_argument("--start_date_str", type=str, required=True)
parser.add_argument("--predict_days", type=int, required=True)
parser.add_argument("--pollen_emiss_path", type=str, required=True)
parser.add_argument("--area", type=str, required=True)
parser.add_argument("--param_root", type=str, required=True)
parser.add_argument("--pft_file", type=str, required=True)
parser.add_argument("--ef_root", type=str, required=True)
parser.add_argument("--ef_chen_root", type=str, required=True)
parser.add_argument("--temp_root", type=str, required=True)
parser.add_argument("--cache_dir", type=str, required=True)
args = parser.parse_args()
start_date_str = args.start_date_str
predict_days   = args.predict_days
pollen_emiss_path = args.pollen_emiss_path
area              = args.area
print(f"收到参数：start_date_str = {start_date_str}, predict_days = {predict_days}")

# 解析起始日期
start_date = datetime.datetime.strptime(start_date_str, '%Y%m%d')
emiss_date     = start_date - timedelta(days=1)
emiss_date_str = emiss_date.strftime("%Y%m%d")
year   = emiss_date.year
monday = emiss_date.strftime('%m%d')
start_doy = (start_date - datetime.datetime(year, 1, 1)).days  # 计算年积日（1月1日为0）
# print('start_doy', start_doy)

lat_lon_res = [
    {"lat_lon_ranges": (35, 45, 111, 121), "res": 0.1}
]
item = lat_lon_res[0]
lat_min, lat_max, lon_min, lon_max = item["lat_lon_ranges"]
res = item["res"]
is_or_not_0p25 = '' if res == 0.1 else '_0p25'
# print(f"处理范围：lat {lat_max}-{lat_min}, lon {lon_max}-{lon_min}, 分辨率：{res}")
shape1, shape2 = int((lat_max - lat_min) / res + 1), int((lon_max - lon_min) / res + 1)
lat = np.linspace(lat_min, lat_max, shape1)
lon = np.linspace(lon_min, lon_max, shape2)
index_lat, column_lon = lat, lon
xlon, xlat = np.meshgrid(lon, lat)  # 最终需要插值到的网格点经纬度

####读取参数，模拟s/eDOY
path_params = os.path.join(args.param_root, '')
'''differential_evolution, dual_annealing'''
'''phen_cdd, phen_TPMt'''
''' , -5'''
algorithm, method, tem_sliding = 'differential_evolution', 'phen_TPMt', ''  ####待修改参数
tem_path_obs = os.path.join(args.temp_root, 'OBS', str(year), '')
tem_path_era5 = os.path.join(args.temp_root, 'ERA5', str(year), '')
tem_path_gfs = os.path.join(args.temp_root, 'GFS', str(year), '')

cache_dir = os.path.join(args.cache_dir, str(start_date.year))
os.makedirs(cache_dir, exist_ok=True)
cache_file = os.path.join(cache_dir, f"running_cache.pkl")
use_cache = os.path.exists(cache_file)

# 在循环开始前，初始化 cache
need_restart = False
cache_save = {}
ds_all = xr.Dataset()
for spec in ['TotPC', 'Artemisia', 'Chenopods']:
    print(f"✅ 正在处理物种：{spec}")
    prefix = spec     # 构造变量名称前缀

    params_path = path_params + f'{spec}/Rsbase_seday_Tbase_start_sim_BJ_1/{algorithm}/{method}_1{tem_sliding}.txt'
    with open(params_path, 'r') as file:
        file_content = file.read()
    match = re.search(r'Optimal parameters: (.*)', file_content)
    if match:
        optimal_params = [float(value.strip()) for value in match.group(1).split(',')]
    if method == 'phen_cdd':
        Rs_base_s, Rs_base_e, Tbase, start_day = optimal_params
    else:
        Rs_base_s, Rs_base_e, Tbase, start_day, a, b = optimal_params
    start_day = round(start_day)
    # print(spec, start_day)

    # print("start_doy", start_doy)
    # 标志变量：是否需要重头开始
    if use_cache:
        try:
            print(f"🟢 加载缓存：{cache_file}")
            with open(cache_file, "rb") as f:
                cache = pickle.load(f)
                start_date_save = cache["start_date"]
            # 检查是否是前一天
            if isinstance(start_date_save, datetime.datetime) and \
                    start_date == start_date_save + datetime.timedelta(days=1):
                print("✅ 缓存日期是前一天，继续加载其他缓存变量并执行代码")
                Rs_obs = cache[f'{prefix}_Rs_obs']
                started = cache[f'{prefix}_started']
                accD    = cache[f'{prefix}_accD']
                started_pre = np.zeros((shape1, shape2), dtype=bool)
                accD_pre    = np.zeros((shape1, shape2), dtype=bool)
                sDOY_map = cache[f'{prefix}_sDOY_map']
                sDOY_map_80 = cache[f'{prefix}_sDOY_map_80']
                eDOY_map = cache[f'{prefix}_eDOY_map']
                eDOY_map_final = cache[f'{prefix}_eDOY_map_final']
                s_est_map = np.full((predict_days + 2, shape1, shape2), -1)
                s_est_map_80 = np.full((predict_days + 2, shape1, shape2), -1)
                e_est_map = np.full((predict_days + 2, shape1, shape2), -1)
                pft_interp = cache[f'{prefix}_pft_interp']
                dur_map = cache[f'{prefix}_dur_map']
                ef = cache[f'{prefix}_ef']

                old_pollen_flux = cache[f'{prefix}_pollen_flux']
                days_list = list(range(start_doy-1, start_doy + predict_days + 1))
                pollen_flux = np.zeros((len(old_pollen_flux) + len(days_list), shape1, shape2))
                pollen_flux[:len(old_pollen_flux)] = old_pollen_flux  # 保留历史
                # flux_start_index = len(old_pollen_flux)  # 当前新的一轮起始索引
                if spec == 'TotPC':
                    flux_start_index1 = len(old_pollen_flux)
                elif spec == 'Artemisia':
                    flux_start_index2 = len(old_pollen_flux)
                else:
                    flux_start_index3 = len(old_pollen_flux)
                print(f"🟢 从 {start_doy} 继续累计计算")
            else:
                print(start_date_save)
                print("⚠️ 缓存日期不匹配，准备重新初始化")
                need_restart = True
        except Exception as e:
            print(f"⚠️ 加载缓存失败：{e}")
            need_restart = True
    else:
        need_restart = True


    # ✅ 最后统一处理重头开始
    if need_restart:
        print("🔄 初始化变量，从头开始累计计算")
        ###读取pft数据  CLM数据
        file_pft = args.pft_file
        data_pft = nc.Dataset(file_pft, 'r')
        pft = data_pft.variables['PCT_PFT'][:]          #0.05×0.05, global data
        pft_lat = data_pft.variables['LAT'][:]          #one dimension 3600
        pft_lon = data_pft.variables['LON'][:]          #one dimension 7200
        lon_lat = (70, 150, 10, 60)
        lon_pft, lat_pft, Wlon_ind, Elon_ind, Slat_ind, Nlat_ind = Reduce_scope(pft_lon, pft_lat, lon_lat)
        pft_CHA = pft[:, Slat_ind:Nlat_ind+1, Wlon_ind:Elon_ind+1]
        pft_C3 = 0.5 * pft_CHA[12] + pft_CHA[13]
        pft_C4 = pft_CHA[14]
        pft_grass = pft_C3 + pft_C4
        lon_pft, lat_pft = np.round(lon_pft, 3), np.round(lat_pft, 3)
        lon_pft, lat_pft = np.meshgrid(lon_pft, lat_pft)
        pft_interp = np.zeros((len(lat), len(lon)))
        if spec == 'TotPC':
            pft_interp = bilinear_interpolation(lon_pft.flatten(), lat_pft.flatten(), pft_grass.flatten(), xlon, xlat)
        else:
            pft_interp = bilinear_interpolation(lon_pft.flatten(), lat_pft.flatten(), pft_C3.flatten(), xlon, xlat)

        if spec == 'Chenopods':
            ef_path = os.path.join(args.ef_chen_root, '')
        else:
            ef_path = os.path.join(args.ef_root, '')
        ###读取季节产量ef
        df = pd.read_csv(ef_path + f'{year}_{spec}_grid_2d_xgb1.csv',index_col=0)
        # df = pd.read_csv(ef_path + f'{year}_TotPC_grid_2d_xgb1.csv', index_col=0)
        if df.shape == pft_interp.shape:
            ef = df.values * np.sqrt(pft_interp)
        else:
            raise ValueError(f"❌ 维度不一致：df.values.shape = {df.values.shape}, pft_interp.shape = {pft_interp.shape}")

        # 初始化
        Rs_obs = np.zeros((shape1, shape2))
        started     = np.zeros((shape1, shape2), dtype=bool)
        accD        = np.full((shape1, shape2), -1)
        started_pre = np.zeros((shape1, shape2), dtype=bool)
        accD_pre    = np.full((shape1, shape2), -1)
        sDOY_map    = np.full((shape1, shape2), -1)
        sDOY_map_80 = np.full((shape1, shape2), -1)
        eDOY_map    = np.full((shape1, shape2), -1)
        eDOY_map_final = np.full((shape1, shape2), -1)
        s_est_map    = np.full((predict_days + 2, shape1, shape2), -1)
        s_est_map_80 = np.full((predict_days + 2, shape1, shape2), -1)
        e_est_map    = np.full((predict_days + 2, shape1, shape2), -1)
        A_map = np.full((shape1, shape2), -1.0)
        dur_map = np.full((shape1, shape2), -9999.)
        days_list = list(range(start_day, start_doy + predict_days + 1))
        pollen_flux = np.zeros((len(days_list), shape1, shape2))
        flux_start_index1, flux_start_index2, flux_start_index3 = 0, 0, 0

    for n, day in tqdm(enumerate(days_list), total=len(days_list)):
        if spec == 'TotPC':
            idx = flux_start_index1 + n
        elif spec == 'Artemisia':
            idx = flux_start_index2 + n
        else:
            idx = flux_start_index3 + n
        current_date = datetime.datetime(year, 1, 1) + datetime.timedelta(days=day)
        yearmonday   = current_date.strftime('%Y%m%d')
        # print(yearmonday)

        file_path_obs = tem_path_obs + f'{yearmonday}/TEM_Avg.csv'
        file_path_era5 = tem_path_era5 + f'{yearmonday}/TEM_Avg.csv'
        file_path_gfs = tem_path_gfs + f'{yearmonday}/{yearmonday}/TEM_Avg.csv'

        last_obs_day = start_doy - 1
        # 根据日期选择数据路径 - 双路径逻辑
        if day <= last_obs_day:  # start_doy及之前使用原始路径

            if os.path.exists(file_path_era5):
                df_tem = pd.read_csv(file_path_era5, index_col=0, encoding="utf-8", low_memory=False)
            elif os.path.exists(file_path_obs):
                df_tem = pd.read_csv(file_path_obs, index_col=0, encoding="utf-8", low_memory=False)
            elif os.path.exists(file_path_gfs):
                df_tem = pd.read_csv(file_path_gfs, index_col=0, encoding="utf-8", low_memory=False)
            else:
                raise FileNotFoundError(f"No TEM_Avg.csv found for {yearmonday} and surrounding days in OBS file.")

            tem_arr = df_tem.values
            for i in range(shape1):
                for j in range(shape2):
                    Ti = tem_arr[i, j]
                    if not started[i, j]:
                        if Ti < Tbase:
                            started[i, j] = True
                            accD[i, j] = day  ###累积开始的第0天
                    if started[i, j]:
                        Rs_obs[i, j] += senescence_rate_sig(Ti, a, b)

                        if sDOY_map_80[i, j] == -1:
                            if Rs_obs[i, j] >= Rs_base_s * 0.8:
                                sDOY_map_80[i, j] = day
                            # else:
                            if (day - accD[i, j]) >= 5 and accD[i, j] != -1:
                                sigma_pre = (day - accD[i, j]) / 4 * (Rs_base_e - Rs_base_s) / Rs_obs[i, j]
                                pdf_2_5 = ef[i, j] * 1 / (np.sqrt(2 * np.pi) * sigma_pre) * np.exp(-1.96 ** 2 / 2)
                                pollen_flux[idx, i, j] = Rs_obs[i, j] / Rs_base_s * pdf_2_5

                        elif sDOY_map[i, j] == -1:  ##sDOY_map_80[i, j] != -1
                            if Rs_obs[i, j] >= Rs_base_s:
                                sDOY_map[i, j] = day
                            # else:
                            if (day - accD[i, j]) >= 5 and accD[i, j] != -1:
                                sigma_pre = (day - accD[i, j]) / 4 * (Rs_base_e - Rs_base_s) / Rs_obs[i, j]
                                pdf_2_5 = ef[i, j] * 1 / (np.sqrt(2 * np.pi) * sigma_pre) * np.exp(-1.96 ** 2 / 2)
                                pollen_flux[idx, i, j] = Rs_obs[i, j] / Rs_base_s * pdf_2_5

                        elif eDOY_map_final[i, j] == -1:
                            if Rs_obs[i, j] < Rs_base_e:
                                # eDOY 还没达到，使用插值预测
                                eDOY_map[i, j] = int(
                                    (day - sDOY_map[i, j]) * (Rs_base_e - Rs_base_s) / (Rs_obs[i, j] - Rs_base_s) +
                                    sDOY_map[i, j])
                                if eDOY_map[i, j] > 340:
                                    eDOY_map[i, j] = 340
                            else:
                                # eDOY 达到，直接赋值
                                eDOY_map[i, j] = day  #####临时存储，随着循环会改变
                                eDOY_map_final[i, j] = day  #####最终存储，随着循环被赋值之后就不会改变了，达到Rs_base_e后的真是eDOY

                            dur_map[i, j] = eDOY_map[i, j] - sDOY_map[i, j]
                            mu = (eDOY_map[i, j] + sDOY_map[i, j]) / 2
                            sigma = (eDOY_map[i, j] - sDOY_map[i, j]) / 4
                            total_gauss = norm(mu, sigma).cdf(eDOY_map[i, j]) - norm(mu, sigma).cdf(sDOY_map[i, j])
                            AAA = ef[i, j] / total_gauss
                            pollen_flux[idx, i, j] = AAA * norm.pdf(day, mu, sigma)

                        elif Rs_obs[i, j] >= Rs_base_e:
                            dur_map[i, j] = eDOY_map_final[i, j] - sDOY_map[i, j]
                            mu = (eDOY_map_final[i, j] + sDOY_map[i, j]) / 2
                            sigma = (eDOY_map_final[i, j] - sDOY_map[i, j]) / 4
                            total_gauss = norm(mu, sigma).cdf(eDOY_map_final[i, j]) - norm(mu, sigma).cdf(
                                sDOY_map[i, j])
                            AAA = ef[i, j] / total_gauss
                            pollen_flux[idx, i, j] = AAA * norm.pdf(day, mu, sigma)
            eDOY_map[eDOY_map_final != -1] = eDOY_map_final[eDOY_map_final != -1]

        else:  ###仅计算和输出pollen_flux，其他变量如sDOY, eDOY, dur都不保存和输出，输出未来pre_day天的sDOY(day, i, j)
            if day == start_doy:
                Rs_gfs = Rs_obs.copy()
                s_est_map[0, :, :] = sDOY_map[:, :]
                e_est_map[0, :, :] = eDOY_map[:, :]
                s_est_map_80[0, :, :] = sDOY_map_80[:, :]
            pre_i = day - start_doy + 1
            # print('pre_i:', pre_i)
            file_path_gfs = tem_path_gfs + f'{start_date_str}/{yearmonday}/TEM_Avg.csv'
            if os.path.exists(file_path_gfs):
                df_tem = pd.read_csv(file_path_gfs, index_col=0, encoding="utf-8", low_memory=False)
            else:
                raise FileNotFoundError(f"No TEM_Avg.csv found for {yearmonday}  in GFS file.")

            tem_arr = df_tem.values
            for i in range(shape1):
                for j in range(shape2):
                    Ti = tem_arr[i, j]
                    should_accumulate = False
                    if not started[i, j]:  #####说明在obs温度下该网格点还没达到开始积温的日期
                        if not started_pre[i, j]:  #####说明在gfs温度下该网格点“也”没达到开始积温的日期
                            if Ti < Tbase:
                                started_pre[i, j] = True
                                accD_pre[i, j] = day  ######每次整个文件循环前都必须有accD_pre[i, j] == -1
                        if started_pre[i, j]:
                            should_accumulate = True
                    else:  ####说明在obs温度下已经达到了开始积温的日期
                        should_accumulate = True
                        accD_pre[i, j] = accD[i, j]

                    if should_accumulate:
                        if isinstance(Ti, str):
                            print("Ti 是字符串", Ti, yearmonday, i, j)
                        Rs_gfs[i, j] += senescence_rate_sig(Ti, a, b)
                        # 情况1：观测阶段未达到sDOY的80%,  即sDOY_map_80[i, j] == -1, 那么一定有sDOY_map==-1, 观测阶段还未达到sDOY
                        if sDOY_map_80[
                            i, j] == -1:  ###如果sDOY_map_80[i, j] == -1,  那么一定有sDOY_map[i, j] == -1, s_est_map_80[1, i, j]==-1
                            if s_est_map_80[pre_i, i, j] == -1:
                                if Rs_gfs[i, j] >= Rs_base_s * 0.8:
                                    s_est_map_80[pre_i:, i, j] = day
                            # else:
                            if (day - accD[i, j]) >= 5 and accD[i, j] != -1:
                                sigma_pre = (day - accD[i, j]) / 4 * (Rs_base_e - Rs_base_s) / Rs_gfs[i, j]
                                pdf_2_5 = ef[i, j] * 1 / (np.sqrt(2 * np.pi) * sigma_pre) * np.exp(-1.96 ** 2 / 2)
                                pollen_flux[idx, i, j] = Rs_gfs[i, j] / Rs_base_s * pdf_2_5

                        # 情况2：观测阶段未达到 sDOY,  即sDOY_map==-1,  那么一定有eDOY_map==-1，obs温度阶段还没达到eDOY
                        ########观测阶段未达到 sDOY,  但一定达到了sDOY的80%,  即sDOY_map_80[i, j] != -1
                        elif sDOY_map[i, j] == -1:  ######说明obs温度下该网格点还没达到sDOY日期，那么gfs温度下刚开始该网格点也没达到sDOY日期
                            s_est_map_80[pre_i:, i, j] = sDOY_map_80[i, j]
                            if s_est_map[
                                pre_i, i, j] == -1:  ######每次整个文件循环前都必须有s_est_map[0, i, j] == -1, 表示观测阶段还未达到花粉开始日期
                                if Rs_gfs[i, j] >= Rs_base_s:
                                    s_est_map[pre_i:, i, j] = day  #### 首次达到 Rs_base_s 的日期, gfs温度阶段达到了sDOY,仅用作gfs阶段计算
                                    # if i == 80 and j == 140:
                                    #     print('***********', s_est_map[pre_i:, i, j])     ###只会输出一次
                                # else:
                                if (day - accD[i, j]) >= 5 and accD[i, j] != -1:
                                    sigma_pre = (day - accD[i, j]) / 4 * (Rs_base_e - Rs_base_s) / Rs_gfs[i, j]
                                    pdf_2_5 = ef[i, j] * 1 / (np.sqrt(2 * np.pi) * sigma_pre) * np.exp(-1.96 ** 2 / 2)
                                    pollen_flux[idx, i, j] = Rs_gfs[i, j] / Rs_base_s * pdf_2_5
                            elif eDOY_map_final[i, j] == -1:  #### eDOY_map_final[i, j] != -1  即Rs[i, j] >= Rs_base_e
                                if Rs_gfs[i, j] < Rs_base_e:  #### eDOY 还没达到，使用插值预测
                                    e_est = int((day - s_est_map[pre_i, i, j]) * (Rs_base_e - Rs_base_s) / (
                                                Rs_gfs[i, j] - Rs_base_s) + s_est_map[pre_i, i, j])
                                    e_est_map[pre_i, i, j] = e_est
                                else:  # eDOY 达到，直接赋值
                                    # e_est = day  #####临时存储，随着循环会改变，仅用作gfs阶段使用，无需保存
                                    # e_est_map[pre_i:, i, j] = day  #####仅用作gfs阶段使用
                                    if e_est_map[pre_i, i, j] == -1:
                                        e_est = day
                                        e_est_map[pre_i:, i, j] = day

                                mu = (e_est + s_est_map[pre_i, i, j]) / 2
                                sigma = (e_est - s_est_map[pre_i, i, j]) / 4
                                total_gauss = norm(mu, sigma).cdf(e_est) - norm(mu, sigma).cdf(s_est_map[pre_i, i, j])
                                AAA = ef[i, j] / total_gauss
                                pollen_flux[idx, i, j] = AAA * norm.pdf(day, mu, sigma)

                            elif eDOY_map_final[i, j] != -1:  #####这行代码不会被执行，因为观测阶段未达到sDOY，肯定也不会达到eDOY
                                print('test print: ***************')
                                mu = (eDOY_map[i, j] + sDOY_map[i, j]) / 2
                                sigma = (eDOY_map[i, j] - sDOY_map[i, j]) / 4
                                total_gauss = norm(mu, sigma).cdf(eDOY_map[i, j]) - norm(mu, sigma).cdf(sDOY_map[i, j])
                                AAA = ef[i, j] / total_gauss
                                pollen_flux[idx, i, j] = AAA * norm.pdf(day, mu, sigma)

                        # ----------------------
                        # 情况3：观测阶段有 sDOY，但无 eDOY
                        elif sDOY_map[i, j] != -1 and eDOY_map_final[i, j] == -1:
                            s_est_map_80[pre_i:, i, j] = sDOY_map_80[i, j]
                            s_est_map[:, i, j] = sDOY_map[i, j]  ###gfs温度阶段继承obs阶段得到的sDOY值
                            if Rs_gfs[i, j] < Rs_base_e:
                                e_est = int(
                                    (day - sDOY_map[i, j]) * (Rs_base_e - Rs_base_s) / (Rs_gfs[i, j] - Rs_base_s) +
                                    sDOY_map[i, j])
                                e_est_map[pre_i, i, j] = e_est
                            else:
                                # e_est = day
                                # e_est_map[pre_i:, i, j] = day
                                if e_est_map[pre_i, i, j] == -1:
                                    e_est = day
                                    e_est_map[pre_i:, i, j] = day
                            mu = (e_est + sDOY_map[i, j]) / 2
                            sigma = (e_est - sDOY_map[i, j]) / 4
                            total_gauss = norm(mu, sigma).cdf(e_est) - norm(mu, sigma).cdf(sDOY_map[i, j])
                            AAA = ef[i, j] / total_gauss
                            pollen_flux[idx, i, j] = AAA * norm.pdf(day, mu, sigma)

                        # ----------------------
                        # 情况4：sDOY 和 eDOY 都已确定（来自观测阶段）
                        elif sDOY_map[i, j] != -1 and eDOY_map_final[i, j] != -1:
                            s_est_map_80[pre_i:, i, j] = sDOY_map_80[i, j]
                            s_est_map[:, i, j] = sDOY_map[i, j]
                            e_est_map[:, i, j] = eDOY_map_final[i, j]

                            mu = (eDOY_map_final[i, j] + sDOY_map[i, j]) / 2
                            sigma = (eDOY_map_final[i, j] - sDOY_map[i, j]) / 4
                            total_gauss = norm(mu, sigma).cdf(eDOY_map_final[i, j]) - norm(mu, sigma).cdf(
                                sDOY_map[i, j])
                            AAA = ef[i, j] / total_gauss
                            pollen_flux[idx, i, j] = AAA * norm.pdf(day, mu, sigma)


        if day == last_obs_day:
            # print(day, idx, start_doy-start_day)    ###39, 40
            Rs_obs_save, started_save, sDOY_map_save, eDOY_map_save, eDOY_map_final_save = Rs_obs, started, sDOY_map, eDOY_map, eDOY_map_final
            pollen_flux_save, day_save, pft_interp_save, dur_map_save, accD_save = pollen_flux[:idx+1, :, :], day, pft_interp, dur_map, accD
            start_date_save, sDOY_map_80_save = start_date, sDOY_map_80
            #####更新cache
            cache_save.update({
                f'{prefix}_Rs_obs': Rs_obs_save,
                f'{prefix}_started': started_save,
                f'{prefix}_sDOY_map': sDOY_map_save,
                f'{prefix}_eDOY_map': eDOY_map_save,
                f'{prefix}_eDOY_map_final': eDOY_map_final_save,
                f'{prefix}_pollen_flux': pollen_flux_save,
                f'{prefix}_pft_interp': pft_interp_save,
                f'{prefix}_dur_map': dur_map_save,
                f'{prefix}_ef': ef,
                f'{prefix}_accD': accD_save,
                "start_date": start_date_save,
                f'{prefix}_sDOY_map_80': sDOY_map_80_save,
            })

    pollen_flux_pre = pollen_flux[-(predict_days+2):, :, :]

    time_dim = f'times_{prefix}'
    days_list_time = list(range(start_day, start_doy + predict_days + 1))
    times = time_date(year, days_list_time)
    ds_all[time_dim] = ((time_dim), times)
    ds_all[f'{prefix}_pollen_flux'] = ((time_dim, 'lat', 'lon'), pollen_flux)

    ds_all[f'{prefix}_pollen_flux_pre'] = (('times_pre', 'lat', 'lon'), pollen_flux_pre)
    ds_all[f'{prefix}_s_est_map'] = (('times_pre', 'lat', 'lon'), s_est_map)
    ds_all[f'{prefix}_s_est_map_80'] = (('times_pre', 'lat', 'lon'), s_est_map_80)
    ds_all[f'{prefix}_e_est_map'] = (('times_pre', 'lat', 'lon'), e_est_map)
    ds_all[f'{prefix}_sDOY'] = (('lat', 'lon'), sDOY_map)
    ds_all[f'{prefix}_sDOY_80'] = (('lat', 'lon'), sDOY_map_80)
    ds_all[f'{prefix}_eDOY'] = (('lat', 'lon'), eDOY_map)
    ds_all[f'{prefix}_eDOY_final'] = (('lat', 'lon'), eDOY_map_final)
    ds_all[f'{prefix}_dur'] = (('lat', 'lon'), dur_map)
    ds_all[f'{prefix}_ef'] = (('lat', 'lon'), ef.data)
    # 添加变量属性
    ds_all[f'{prefix}_pollen_flux_pre'].attrs = {'long_name': 'pollen emission potential (flux)',
                                   'coordinates': 'lat lon',
                                    'units': 'grains m-2 day-1'}
    ds_all[f'{prefix}_pollen_flux'].attrs = {'long_name': 'pollen emission potential (flux)',
                                       'coordinates': 'lat lon',
                                        'units': 'grains m-2 day-1'}

    ds_all[time_dim].attrs = {'long_name': time_dim,
                             'units': 'days since 1900-01-01',
                             'calendar': 'gregorian'}


with open(cache_file, 'wb') as f:
    pickle.dump(cache_save, f)
print("✅ 所有物种数据缓存已保存")

days_list_pre = list(range(start_doy - 1, start_doy + predict_days + 1))
times_pre     = time_date(year, days_list_pre)

ds_all['xlat'] = (('lat'), lat)
ds_all['xlon'] = (('lon'), lon)
ds_all['times_pre'] = (('times_pre'), times_pre)
ds_all['xlat'].attrs = {'long_name': 'latitude coordinate',
                        'standard_name': 'latitude',
                        'units': 'degrees_north'}
ds_all['xlon'].attrs = {'long_name': 'longitude coordinate',
                        'standard_name': 'longitude',
                        'units': 'degrees_east'}
ds_all['times_pre'].attrs = {'long_name': 'times_pre',
                             'units': 'days since 1900-01-01',
                             'calendar':'gregorian'}

os.makedirs(pollen_emiss_path, exist_ok=True)
ds_all.to_netcdf(pollen_emiss_path + f'/{area}_emission_{emiss_date_str}_pre{predict_days}.nc')








