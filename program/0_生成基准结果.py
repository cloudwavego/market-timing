"""
币圈择时小组第2期专属代码
author: 邢不行
微信: xbx9585
"""
import warnings
from datetime import datetime
from datetime import timedelta
from multiprocessing import Pool, cpu_count

from Config import *
from Evaluate import *
from Function import *
from Statistics import *


def calculate_by_one_loop(symbol):
    """
    处理每个传递进来的币种
    :param symbol: 币种名称，是一个字符串，对应我们全量数据中币种的文件名，注意：不包含.csv
    :return:
        返回币种的回测结果，包含累积币种名称、净值、年化收益最大回撤、年化收益回撤比字段
    """
    warnings.filterwarnings('ignore')
    print(symbol)
    # ===== 读取数据
    # === 读取原始的csv数据
    df = pd.read_csv(os.path.join(symbol_data_path, symbol + '.csv'), encoding='gbk', parse_dates=['candle_begin_time'],
                     skiprows=1)  # 用GBK编码读取csv文件，跳过第一行并把candle_begin_time转化为日期格式
    # === 对数据进行去重、排序
    # 任何原始数据读入都进行一下排序、去重，以防万一
    df.drop_duplicates(subset=['candle_begin_time'], inplace=True)  # 对数据根据candle_begin_time去重
    df.sort_values(by=['candle_begin_time'], inplace=True)  # 根据candle_begin_time对数据进行排序
    df.reset_index(inplace=True, drop=True)  # 重新设置index

    # === 转换数据周期
    period_df = df.resample(rule=rule_type, on='candle_begin_time', label='left', closed='left').agg(
        {'open': 'first',
         'high': 'max',
         'low': 'min',
         'close': 'last',
         'volume': 'sum',
         'quote_volume': 'sum',
         'trade_num': 'sum',
         'taker_buy_base_asset_volume': 'sum',
         'taker_buy_quote_asset_volume': 'sum',
         })  # 将原始的df数据转换为指定的时间周期，指定转换周期的日期列为candle_begin_time并指定各个列的转换规则
    # 'open': 'first' 即将open的第一个数据作为开盘价，常用的有 first：第一个、max 最大值、min 最小值、last 最后一个、sum 所有数据和、mean 均值

    # === 对转换数据周期之后的数据进行筛选
    period_df.dropna(subset=['open'], inplace=True)  # 去除一天都没有交易的周期
    period_df = period_df[period_df['volume'] > 0]  # 去除成交量为0的交易周期
    period_df.reset_index(inplace=True)  # 重新设置一下index

    df = period_df[
        ['candle_begin_time', 'open', 'high', 'low', 'close', 'volume', 'quote_volume', 'trade_num',
         'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume']]  # 筛选一下需要的列，避免把所有的列都存在内存中，避免加大内存的压力

    # === 对数据进行时间筛选
    # 保留币种上线N天之后的日期
    t = df.iloc[0]['candle_begin_time'] + timedelta(days=drop_days)  # 获取第一行数据的日期，并且加上我们指定的天数
    df = df[df['candle_begin_time'] > t]  # 筛选时间
    df = df[df['candle_begin_time'] >= pd.to_datetime(date_start)]  # 筛选时间大于等于我们指定的回测开始时间
    df = df[df['candle_begin_time'] <= pd.to_datetime(date_end)]  # 筛选时间小于等于我们指定的回测结束时间
    df.reset_index(inplace=True, drop=True)# 重新设置一下index

    # ===== 计算资金曲线
    # === 设置持有信号
    df['pos'] = 1  # 强制设置持有为1，即从回测开始买入，一直持有

    # === 计算资金曲线
    min_amount = min_amount_dict[symbol.replace('-', '')]  # 获取最小下单量
    df = cal_equity_curve(df, slippage=slippage, c_rate=c_rate,
                          leverage_rate=leverage_rate,
                          min_amount=min_amount,
                          min_margin_ratio=min_margin_ratio)  # 计算资金曲线

    # === 策略评价
    original_trade = transfer_equity_curve_to_trade(df)  # 将含有资金曲线的df转化为每笔交易
    original, _ = strategy_evaluate(df, original_trade)  # 计算策略各种评价指标
    # === 保存需要的指标数据
    rtn = pd.DataFrame()  # 创建一个空的df对象
    rtn.loc[0, '币种'] = symbol  # 保存币种名称
    rtn.loc[0, '累积净值'] = original.loc['累积净值', 0]  # 保存累积净值
    rtn.loc[0, '年化收益'] = original.loc['年化收益', 0]  # 保存年化收益
    rtn.loc[0, '最大回撤'] = original.loc['最大回撤', 0]  # 保存最大回撤
    rtn.loc[0, '年化收益/回撤比'] = original.loc['年化收益/回撤比', 0]  # 保存年化收益回撤比
    return rtn


if __name__ == '__main__':
    # ==== 循环指定的时间周期
    for rule_type in ['4H']:

        # ==== 回测主程序
        start_time = datetime.now()  # 标记开始时间

        multiple_process = True  # 设置是否并行，True为并行，False为串行

        # === 开始进行回测
        if multiple_process:
            with Pool(max(cpu_count() - 1, 1)) as pool:
                # 使用并行批量获得data frame的一个列表
                df_list = pool.map(calculate_by_one_loop, symbol_list)
        else:
            df_list = []  # 定义一个空的列表，用来保存回测的结果

            # 循环每个币种
            for symbol in symbol_list:
                res_df = calculate_by_one_loop(symbol=symbol)  # 调用回测的函数，返回回测结果
                df_list.append(res_df)  # 将回测结果累加到df_list，用于后续合并大表使用
        print('读入完成, 开始合并', datetime.now() - start_time)  # 回测结束，输出一下使用的时间

        # ==== 整理回测后的数据
        # === 将df_list内所有的回测结果合并，作为一个大表，并重新设置一下index
        para_curve_df = pd.concat(df_list, ignore_index=True)  # 合并为一个大的DataFrame

        # === 对数据进行排序
        para_curve_df.sort_values(by='年化收益/回撤比', ascending=False, inplace=True)  # 将数据根据年化收益回撤比降序排序
        print(para_curve_df.head(10))  # 输出前10行数据

        # === 保存回测后的结果
        p = root_path + '/data/output/para/基准&%s&%s.csv' % (leverage_rate, rule_type)  # 拼接数据保存的路径
        para_curve_df.to_csv(p, index=False, encoding='gbk')  # 以GBK编码并且删除index保存csv文件
