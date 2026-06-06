import hashlib
import multiprocessing
import os
import pickle
import sys
import re
import logging
from datetime import datetime, timedelta
from multiprocessing import Pool
import numpy as np
import xarray as xr
#import xesmf as xe
import netCDF4 as nc
import argparse

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("make_meic_wrfchemi")

parser = argparse.ArgumentParser()
parser.add_argument("--start_date_str", type=str, required=True)
parser.add_argument("--predict_days", type=int, required=True)
parser.add_argument("--wrfinput_file", type=str, required=True)
parser.add_argument("--domain", type=str, required=True)
parser.add_argument("--meic_save_dir", type=str, required=True)
parser.add_argument("--meic_dir", type=str, required=True)
parser.add_argument("--cache_dir", type=str, required=True)
parser.add_argument("--n_jobs", type=int, default=8)
args = parser.parse_args()

start_date_str = args.start_date_str
predict_days   = args.predict_days
wrfinput_file  = args.wrfinput_file
domain         = args.domain
meic_save_dir  = args.meic_save_dir
meic_dir  = args.meic_dir
cache_dir = args.cache_dir

# print(wrfinput_file)
# 获取脚本所在目录和脚本名称
my_dirname, my_filename = os.path.split(os.path.abspath(sys.argv[0]))
# 其他指定路径
CB05_DIR = meic_dir   #meic dir path


# 将字符串转换为日期对象
date_obj = datetime.strptime(start_date_str, "%Y%m%d")
new_date_obj = date_obj - timedelta(days=2)    # 减去2天
sstart_date_str = new_date_obj.strftime("%Y%m%d")     # 将结果转换回字符串格式
ppredict_days = predict_days+3    ##6天

# meic经纬度,格点的位于每个网格的中心点
lon = np.arange(70.125, 150, 0.25, dtype=np.float32)  
lat = np.arange(10.125,  60, 0.25, dtype=np.float32)
lon, lat = np.meshgrid(lon, lat)

# 排放源高度分布     从11层修改降低至8层
emission_height_distribution = {"agriculture":   [1.000, 0.000, 0.000, 0.000, 0.000, 0.000, 0.000, 0.000],#
                                "industry":      [0.602, 0.346, 0.052, 0.000, 0.000, 0.000, 0.000, 0.000],#
                                "power":         [0.034, 0.140, 0.349, 0.227, 0.167, 0.059, 0.024, 0.000],#
                                "residential":   [0.900, 0.100, 0.000, 0.000, 0.000, 0.000, 0.000, 0.000],#
                                "transportation":[0.950, 0.050, 0.000, 0.000, 0.000, 0.000, 0.000, 0.000]}#
# 排放源时间分布,BJT 0-23
emission_time_distribution = {"agriculture":   [1.000, 1.000, 1.000, 1.000, 1.000, 1.000, 1.000, 1.000, 1.000, 1.000, 1.000, 1.000, 1.000, 1.000, 1.000, 1.000, 1.000, 1.000, 1.000, 1.000, 1.000, 1.000, 1.000, 1.000],
                              "industry":      [0.504, 0.504, 0.504, 0.504, 0.504, 0.648, 0.792, 0.936, 1.080, 1.632, 1.632, 1.632, 1.632, 1.632, 1.632, 1.632, 1.632, 1.080, 0.936, 0.792, 0.648, 0.504, 0.504, 0.504],
                              "power":         [0.840, 0.708, 0.576, 0.600, 0.732, 0.804, 0.852, 0.972, 1.104, 1.200, 1.212, 1.200, 1.224, 1.236, 1.236, 1.224, 1.176, 1.104, 1.116, 1.128, 1.080, 1.008, 0.948, 0.720],
                              "residential":   [0.336, 0.312, 0.408, 0.216, 0.408, 1.080, 1.176, 1.248, 1.224, 1.584, 2.736, 2.520, 0.984, 0.696, 0.552, 0.984, 1.680, 2.328, 1.488, 0.840, 0.264, 0.360, 0.336, 0.240],
                              "transportation":[0.480, 0.348, 0.252, 0.216, 0.192, 0.312, 0.720, 1.416, 1.536, 1.440, 1.392, 1.272, 1.212, 1.368, 1.380, 1.416, 1.428, 1.524, 1.380, 1.128, 1.068, 1.008, 0.864, 0.648]}

# 无机气体的摩尔质量
inorganic_gas_mole_weight = {'CO':28, 'NH3':17, 'NOx':31.6, 'SO2':64}    #NOx中由10%是NO2,90%是NO,所以平均摩尔质量是46*0.1+30*0.9=31.6
# 排放的周内变化。周日为0.
week_emiss_factor = {
    "agriculture":      [1.00,1.00,1.00,1.00,1.00,1.00,1.00],
    "industry":         [0.80,1.08,1.08,1.08,1.08,1.08,0.80],
    "power":            [0.85,1.06,1.06,1.06,1.06,1.06,0.85],
    "residential":      [0.80,1.08,1.08,1.08,1.08,1.08,0.80],
    "transportation":   [0.79,1.02,1.06,1.08,1.10,1.14,0.81]
}
# 计算指定中心纬度的经纬度网格的面积。
def ll_area(lat,res=0.25):
    '''
    input:
        lat: 经纬度网格中心点纬度组成的数组,np.2darray
        res: 经纬度网格分辨率/边长,单位:度
    return:
        面积组成的数组,单位km2.
    TODO:
    沿海地区的经纬度网格内陆地面积应该比网格面积小，实际上的平均排放速率应该通过陆地面积计算。
    以后这里应该直接返回一个numpy数组，因为meic网格和海陆分布是固定的，不需要每次临时计算
    '''
    
    radius_km = 6371.0
    lat1 = np.deg2rad(lat - res / 2.0)
    lat2 = np.deg2rad(lat + res / 2.0)
    dlon = np.deg2rad(res)
    return (radius_km ** 2) * dlon * (np.sin(lat2) - np.sin(lat1))

# 插值程序,从meic网格插值到wrf网格
def meic2wrf(lon_inp,lat_inp,lon,lat,emis):#lon/lat_inp: model; lon/lat: meic; emis: meic emis
    #coordinations of meic grids origin
    ox=lat[0,0]
    oy=lon[0,0]

    def inp(ix, iy, dx, dy, cdx, cdy): #put small function under meic2wrf function, or variables in small functions are global.
        #area_ratio
        return emis[ix,iy]*cdx*cdy+emis[ix,iy+1]*cdx*dy+emis[ix+1,iy+1]*dx*dy+emis[ix+1,iy]*dx*cdy

    def std_p(p,o): #standardize point p
        p = (p-o)*4
        dp = p - int(p)
        cdp = 1 - dp
        ip = int(p) #get index of the nearest big grid relates to the p point
        return dp, cdp, ip

    def inp_p(px, py):
        dx, cdx, ix = std_p(px,ox)
        dy, cdy, iy = std_p(py,oy)
        return inp(ix, iy, dx, dy, cdx, cdy)

    emis_inp=np.zeros(lon_inp.shape, dtype='float32')
    # y_cnt =0
    # for (row_lat, row_lon) in zip(lat_inp, lon_inp): #2D meic coordinates to 1D
    #     x_cnt=0
    #     for (pnt_lat, pnt_lon) in zip(row_lat, row_lon): #1D to point
    #         emis_inp[y_cnt,x_cnt] = inp_p(pnt_lat, pnt_lon) #assign meic emission
    #         x_cnt += 1
    #     y_cnt +=1
    # 输出数组初始化

    # 先生成掩膜：只对范围内的点做插值  范围外的都默认是0
    lat_min, lat_max = lat.min(), lat.max()
    lon_min, lon_max = lon.min(), lon.max()
    mask = (lat_inp >= lat_min) & (lat_inp <= lat_max) & \
           (lon_inp >= lon_min) & (lon_inp <= lon_max)
    # 插值
    for y_cnt, (row_lat, row_lon) in enumerate(zip(lat_inp, lon_inp)):
        for x_cnt, (pnt_lat, pnt_lon) in enumerate(zip(row_lat, row_lon)):
            if mask[y_cnt, x_cnt]:
                emis_inp[y_cnt, x_cnt] = inp_p(pnt_lat, pnt_lon)
    return emis_inp

def avg_hour(iemiss,emiss_year,emiss_month):
    #计算本月有多少个等效小时
    #等效小时： 假设每天都排放系数都相同（都是1），日内每小时的排放都相同，那么等效小时内的排放应该是这个月的总排放除以总小时数。
    #这个值直接乘以各种系数就可以作为排放
    '''
        iemiss: 排放源种类(5种）
        emiss_year,emiss_month:   meic排放源头的时间
    '''
    avg_hour_count = 0  
    start_time = datetime(int(emiss_year),int(emiss_month),1,0)   #本月的开始时间,bjt
    while start_time.strftime("%m") == emiss_month:
        avg_hour_count += week_emiss_factor[iemiss][int(start_time.strftime("%w"))] * emission_time_distribution[iemiss][int(start_time.strftime("%H"))]
        start_time += timedelta(hours=1)
    return avg_hour_count
    #结束


def convert_unit(var,value,iemiss,emiss_year,emiss_month):
    '''
        var:  要变化的变量名
        value: 值，二维数组
        iemiss: 排放源种类(5种）
        emiss_year,emiss_month:   meic排放源头的时间
    '''
    #计算本月有多少个等效小时
    #等效小时: 星期变化和日变化系数都是1的小时
    avg_hour_count = avg_hour(iemiss,emiss_year,emiss_month)
    #结束

    # _,len_month = calendar.monthrange(emiss_year,emiss_month)  #获取排放源对应月份的天数
    if var in ['CO', 'NH3', 'NOx', 'SO2', ]:  #inorganic gas: ton/(grid.month) to mole/(km2.h)
        emiss = value*1e6/(ll_area(lat, 0.25)*avg_hour_count *inorganic_gas_mole_weight[var])
    elif var in ['BC', 'OC', 'PM25', 'PM10', ]:  # aerosol: ton/(grid.month) to ug/(m2.s)
        emiss = value*1e6/(ll_area(lat, 0.25)*avg_hour_count*3600)
    else:  # organic gas: million_mole/(grid.month) to mole/(km2.h)
        emiss = value*1e6/(ll_area(lat, 0.25)*avg_hour_count)
    return emiss  #返回实际上是当月等效小时数

def pickle_read(pickle_file):# 是否存在pickle文件，如果存在则读取
    flag = False
    try:
        with open(pickle_file,"rb") as f:
            return_dict = pickle.load(f)
        flag = True
        logger.info("success load "+pickle_file)
    except:
        return_dict = {}
    return flag,return_dict

def md5_value(file_name):   #计算wrfinput文件的md5值
    '''
    每一个wrfinput文件都拥有唯一的md5值
    通过md5区分不同wrfinput对应的interp_meic_emission
    '''
    with open(file_name, 'rb') as fp:
        data = fp.read()
    file_md5= hashlib.md5(data).hexdigest()
    return file_md5

def make_interp_meic_emission(emiss_year,emiss_month,md5value,lon_inp,lat_inp):
    print(emiss_year,emiss_month)
    pickle_dir = cache_dir
    os.makedirs(pickle_dir, exist_ok=True)
    flag,interp_meic_emission = pickle_read(pickle_dir+"/"+emiss_year+emiss_month+"_"+str(md5value)+".pickle")  #插值到wrf格点并进行过单位变换的meic变量
    if not flag:
        # 获取meic数据,并转化单位
        for spec in ['CO', 'NH3', 'NOx', 'SO2',
                     # 'RADM2_ALD', 'RADM2_CSL', 'RADM2_ETH',
                     # 'RADM2_HC3', 'RADM2_HC5', 'RADM2_HC8', 'RADM2_HCHO', 'RADM2_ISO',
                     # 'RADM2_KET', 'RADM2_HC5', 'RADM2_OL2', 'RADM2_OLI', 'RADM2_OLT', 'RADM2_ORA2',
                     # 'RADM2_TOL', 'RADM2_XYL', 'BC', 'OC', 'PM25', 'PMcoarse'
                     ]:      ##修改为RADM2物种名称
            interp_meic_emission[spec]={}
            for iemiss in ["agriculture","industry","power","residential","transportation"]:
                # try:  #部分污染物仅存在于某些类型排放源
                if emiss_month[0] == '0':
                    meic_emis = np.loadtxt(CB05_DIR + "/" + emiss_year + "_" + emiss_month[1] + "_" + iemiss + "_" + spec + ".asc",skiprows=6)[::-1, :]
                    logger.info(emiss_year + "_" + emiss_month[1] + "_" + iemiss + "_" + spec + ".asc read")
                else:
                    meic_emis = np.loadtxt(CB05_DIR+"/"+emiss_year+"_"+emiss_month+"_"+iemiss+"_"+spec+".asc",skiprows = 6)[::-1,:]
                    logger.info(emiss_year+"_"+emiss_month+"_"+iemiss+"_"+spec+".asc read")
                meic_emis = np.where(meic_emis > 0, meic_emis, 0)  #将-9999区域全部转化为0
                meic_emis = convert_unit(var=spec,value=meic_emis,iemiss=iemiss,emiss_year=emiss_year,emiss_month=emiss_month)  #转化单位
                interp_meic_emission[spec][iemiss]={}
                interp_meic_emission[spec][iemiss]["base"] = meic2wrf(lon_inp,lat_inp,lon,lat,meic_emis)
                # except:
                #     pass
        ## 保存interp_meic_emission
        if not os.path.exists(pickle_dir+"/"+emiss_year+emiss_month+"_"+str(md5value)+".pickle"):
            if not os.path.exists(pickle_dir):  
                os.makedirs(pickle_dir)
            with open(pickle_dir+"/"+emiss_year+emiss_month+"_"+str(md5value)+".pickle","wb") as pickle_file:
                pickle.dump(interp_meic_emission,pickle_file)
            logger.info(pickle_dir+"/"+emiss_year+emiss_month+"_"+str(md5value)+".pickle written")
    return

def calculate_wrfchemi_data(x):
    wrfinput_file = x[0]
    wrf_time_utc  = x[1]
    lon_inp       = x[2]
    lat_inp       = x[3]
    md5value      = x[4]
    emiss_year    = x[5]
    '''
        计算单个时间步的排放数据
        wrfinput_file: wrfinput文件路径
        wrf_time_utc: 生成的排放源的时间
    '''
    
    wrf_time_bjt = wrf_time_utc + timedelta(hours=8)
    emiss_month=wrf_time_bjt.strftime('%m')
    logger.info("start calculating "+wrf_time_utc.strftime("%Y-%m-%d_%H:00:00"))

    with open(cache_dir+"/"+emiss_year+emiss_month+"_"+str(md5value)+".pickle","rb") as f:
        interp_meic_emission = pickle.load(f)
    
    # 计算排放数据
    for spec in interp_meic_emission.keys():
        for iemiss in ["agriculture","industry","power","residential","transportation"]:
            try:
                # 应用周变化和日变化系数
                interp_meic_emission[spec][iemiss]["base"] *= week_emiss_factor[iemiss][int(wrf_time_bjt.strftime("%w"))]
                interp_meic_emission[spec][iemiss]["base"] *= emission_time_distribution[iemiss][int(wrf_time_bjt.strftime("%H"))]
                
                # 应用高度层分布
                interp_meic_emission[spec][iemiss]["levels"] = np.zeros((len(emission_height_distribution["power"]),lon_inp.shape[0],lon_inp.shape[1]))
                for ilevel in range(len(emission_height_distribution["power"])):
                    interp_meic_emission[spec][iemiss]["levels"][ilevel,...] = interp_meic_emission[spec][iemiss]["base"] * emission_height_distribution[iemiss][ilevel]
            except:
                pass
            
        # 合并所有排放源
        for ilevel in range(len(emission_height_distribution["power"])):
            interp_meic_emission[spec]["all"] = {}
            interp_meic_emission[spec]["all"]["levels"] = np.zeros((len(emission_height_distribution["power"]),lon_inp.shape[0],lon_inp.shape[1]))
            for iemiss in ["agriculture","industry","power","residential","transportation"]:
                try:
                    interp_meic_emission[spec]["all"]["levels"] += interp_meic_emission[spec][iemiss]["levels"]
                except:
                    pass

    # 构建WRFChem排放数据结构
    wrfchem_emission = {}
    wrfchem_emission["E_CO"] = interp_meic_emission['CO']["all"]["levels"]  # co
    wrfchem_emission["E_NH3"] = interp_meic_emission['NH3']["all"]["levels"]  # nh3
    wrfchem_emission["E_NO"] = interp_meic_emission["NOx"]["all"]["levels"] * 0.9  # no
    wrfchem_emission["E_NO2"] = interp_meic_emission["NOx"]["all"]["levels"] * 0.1  # no2
    wrfchem_emission["E_SO2"]   =  interp_meic_emission["SO2"]["all"]["levels"]                 #so2
    # wrfchem_emission["E_ALD"]   =  interp_meic_emission['RADM2_ALD']["all"]["levels"]              #ald
    # wrfchem_emission["E_CSL"] = interp_meic_emission['RADM2_CSL']["all"]["levels"]  # hcho
    # wrfchem_emission["E_ETH"] = interp_meic_emission['RADM2_ETH']["all"]["levels"]  # eth
    # wrfchem_emission["E_HC3"] = interp_meic_emission['RADM2_HC3']["all"]["levels"] * 0.2  # hc3
    # wrfchem_emission["E_HC5"] = interp_meic_emission['RADM2_HC5']["all"]["levels"] * 0.4  # hc5
    # wrfchem_emission["E_HC8"] = interp_meic_emission['RADM2_HC8']["all"]["levels"] * 0.6  # hc8
    # wrfchem_emission["E_HCHO"] = interp_meic_emission['RADM2_HCHO']["all"]["levels"]  # hcho
    # wrfchem_emission["E_ISO"] = interp_meic_emission['RADM2_ISO']["all"]["levels"]  # eth
    # wrfchem_emission["E_KET"] = interp_meic_emission['RADM2_KET']["all"]["levels"]  # eth
    # wrfchem_emission["E_OL2"] = interp_meic_emission['RADM2_OL2']["all"]["levels"]  # ol2
    # wrfchem_emission["E_OLI"] = interp_meic_emission['RADM2_OLI']["all"]["levels"]  # oli
    # wrfchem_emission["E_OLT"] = interp_meic_emission['RADM2_OLT']["all"]["levels"]  # olt
    # wrfchem_emission["E_ORA2"]  =  interp_meic_emission['RADM2_ORA2']["all"]["levels"]                                #ora2 ##not sure
    # wrfchem_emission["E_TOL"] = interp_meic_emission['RADM2_TOL']["all"]["levels"]  # tol
    # wrfchem_emission["E_XYL"] = interp_meic_emission['RADM2_XYL']["all"]["levels"]  # xyl
    # wrfchem_emission["E_ECI"] = interp_meic_emission['BC']["all"]["levels"] * 0.2  # eci
    # wrfchem_emission["E_ECJ"] = interp_meic_emission['BC']["all"]["levels"] * 0.8  # ecj
    # wrfchem_emission["E_ORGI"] = interp_meic_emission['OC']["all"]["levels"] * 0.2  # orgi
    # wrfchem_emission["E_ORGJ"] = interp_meic_emission['OC']["all"]["levels"] * 0.8  # orgj
    # wrfchem_emission["E_PM25I"] = interp_meic_emission['PM25']["all"]["levels"] * 0.2  # pm2.5i
    # wrfchem_emission["E_PM25J"] = interp_meic_emission['PM25']["all"]["levels"] * 0.8  # pm2.5j
    # wrfchem_emission["E_PM_10"] = interp_meic_emission['PM25']["all"]["levels"] + \
    #                               interp_meic_emission['PMcoarse']["all"]["levels"]  # pm10
    # wrfchem_emission["E_SO4I"] = np.zeros_like(wrfchem_emission["E_SO2"])  # so4i
    # wrfchem_emission["E_SO4J"] = np.zeros_like(wrfchem_emission["E_SO2"])  # so4j
    # wrfchem_emission["E_NO3I"] = np.zeros_like(wrfchem_emission["E_SO2"])  # no3i
    # wrfchem_emission["E_NO3J"] = np.zeros_like(wrfchem_emission["E_SO2"])  # no3j

    return {
        'time': wrf_time_utc,
        'data': wrfchem_emission,
        'lon': lon_inp,
        'lat': lat_inp
    }

def create_combined_file(results, domain, year, mon, day, save_dir):
    # 按时间排序
    results.sort(key=lambda x: x['time'])
    
    # 获取时间列表
    times = [r['time'] for r in results]
    time_strings = [t.strftime('%Y-%m-%d_%H:%M:%S') for t in times]
    
    # 获取第一个结果作为样本
    sample = results[0]
    lon_inp = sample['lon']
    lat_inp = sample['lat']
    
    # 获取所有排放物种
    species_list = list(sample['data'].keys())
    
    # 创建合并后的数据数组
    combined_data = {}
    for spec in species_list:
        # 初始化4D数组 (时间, 层, 南北, 东西)
        combined_data[spec] = np.stack([r['data'][spec] for r in results], axis=0)
    
    # 创建输出文件名
    output_file = os.path.join(save_dir, f'combined_wrfchemi_{domain}_{year}_{mon}_{day}.nc')
    if os.path.exists(output_file):
        os.remove(output_file)
    
    # 创建NetCDF文件
    ncfile = nc.Dataset(output_file, 'w', format='NETCDF4_CLASSIC')
    
    # 创建维度
    n_time = len(times)
    n_zdim = combined_data[species_list[0]].shape[1]
    n_sn = lon_inp.shape[0]
    n_we = lon_inp.shape[1]
    
    ncfile.createDimension('Time', n_time)
    ncfile.createDimension("DateStrLen", 19)
    ncfile.createDimension('emissions_zdim', n_zdim)
    ncfile.createDimension('south_north', n_sn)
    ncfile.createDimension('west_east', n_we)
    
    # 全局属性
    ncfile.setncattr("TITLE", "EMISSIONS for WRF-Chem")
    ncfile.setncattr("MMINLU", "MODIFIED_IGBP_MODIS_NOAH")
    ncfile.setncattr("NUM_LAND_CAT", 20)
    
    # 创建Times变量
    times_var = ncfile.createVariable("Times", 'c', ('Time', 'DateStrLen'))
    for i, ts in enumerate(time_strings):
        # 确保字符串长度为19个字符
        char_array = np.array(list(ts.ljust(19)), 'c')
        times_var[i, :] = char_array
    
    # 创建经纬度变量
    xlat_var = ncfile.createVariable('XLAT', 'f4', ('south_north', 'west_east'))
    xlat_var.setncattr('description', 'LATITUDE, SOUTH IS NEGATIVE')
    xlat_var.setncattr('units', "degree north")
    xlat_var.setncattr('MemoryOrder', 'XYZ')
    xlat_var[:, :] = lat_inp
    
    xlong_var = ncfile.createVariable('XLONG', 'f4', ('south_north', 'west_east'))
    xlong_var.setncattr('description', 'LONGITUDE, WEST IS NEGATIVE')
    xlong_var.setncattr('units', "degree east")
    xlong_var.setncattr('MemoryOrder', 'XYZ')
    xlong_var[:, :] = lon_inp
    
    # 创建每个物种的变量
    for spec in species_list:
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
        var[:, :, :, :] = combined_data[spec]
    
    ncfile.close()
    logger.info(f"Successfully wrote combined file: {output_file}")
    return output_file

def parallel_make_combined_wrfchemi(start_time, end_time, emiss_year, domain, n_jobs=-1):
    # 读取WRF输入文件
    wrfinput_ds = xr.open_dataset(wrfinput_file, engine="netcdf4")
    md5value = md5_value(wrfinput_file)
    lon_inp = wrfinput_ds['XLONG'][0, ...].values
    lat_inp = wrfinput_ds['XLAT'][0, ...].values
    
    # 生成时间列表
    timelist = []
    current_time = start_time
    while current_time <= end_time:
        timelist.append(current_time)
        current_time += timedelta(hours=1)
    
    # 设置并行工作数
    if n_jobs == -1:
        n_jobs = min(args.n_jobs, multiprocessing.cpu_count())
    
    # 预加载需要的月份数据
    month_already = []
    for itime in timelist:
        itime_bjt = itime + timedelta(hours=8)
        month = itime_bjt.strftime("%m")
        if month not in month_already:
            # print(lon_inp, lat_inp)
            # print(len(lon_inp), len(lat_inp))  ###wrfinput中的长度
            make_interp_meic_emission(emiss_year, month, md5value, lon_inp, lat_inp)
            month_already.append(month)
    
    # 准备并行任务
    all_list = []
    for itime in timelist:
        all_list.append([wrfinput_file, itime, lon_inp, lat_inp, md5value, emiss_year])
    
    # 并行计算所有时间步的数据
    with Pool(n_jobs) as p:
        results = p.map(calculate_wrfchemi_data, all_list)
    
    # 提取年月日信息用于文件名
    year = start_time.strftime('%Y')
    mon = start_time.strftime('%m')
    day = start_time.strftime('%d')
    
    # 创建合并文件
    os.makedirs(meic_save_dir, exist_ok=True)
    combined_file = create_combined_file(results, domain, year, mon, day, meic_save_dir)
    return combined_file

if __name__ == '__main__':
    emiss_year = '2017'
    
    # 将字符串转换为datetime对象
    start_time = datetime.strptime(sstart_date_str, "%Y%m%d")
    # 计算结束时间（增加指定天数）
    end_time = start_time + timedelta(days=ppredict_days)
    # 直接生成合并文件
    combined_file = parallel_make_combined_wrfchemi(start_time, end_time, emiss_year, domain, -1)
    print(f"Combined file created: {combined_file}")
