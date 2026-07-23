"""
币圈择时小组第2期专属代码
author: 邢不行
微信: xbx9585
"""
from datetime import timedelta, datetime

import Signals
from Config import *
from Evaluate import *
from Function import *
from Position import *
from Statistics import *

start_time = datetime.now()
# ==== 读入数据
# === 读取原始的csv数据
df = pd.read_csv(os.path.join(symbol_data_path, symbol + '.csv'), encoding='gbk', parse_dates=['candle_begin_time'],
                 skiprows=1)  # 用GBK编码读取csv文件，跳过第一行并把candle_begin_time转化为日期格式

# === 对数据进行去重、排序
# 任何原始数据读入都进行一下排序、去重，以防万一
df.sort_values(by=['candle_begin_time'], inplace=True)  # 对数据根据candle_begin_time去重
df.drop_duplicates(subset=['candle_begin_time'], inplace=True)  # 根据candle_begin_time对数据进行排序
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
df = period_df[['candle_begin_time', 'open', 'high', 'low', 'close', 'volume', 'quote_volume', 'trade_num',
                'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume']]  # 筛选一下需要的列，避免把所有的列都存在内存中，避免加大内存的压力

# === 计算交易信号
df = getattr(Signals, signal_name)(df, para=para, proportion=proportion,
                                   leverage_rate=leverage_rate)  # 调用我们在config里面配置的signal名称生成signal信号

# === 对数据进行时间筛选  计算信号后再筛选数据，避免前面几个周期因为数据量不够导致计算结果为空或失真
# 保留币种上线N天之后的日期
t = df.iloc[0]['candle_begin_time'] + timedelta(days=drop_days)  # 获取第一行数据的日期，并且加上我们指定的天数
df = df[df['candle_begin_time'] > t]  # 筛选时间
df = df[df['candle_begin_time'] >= pd.to_datetime(date_start)]  # 筛选时间大于等于我们指定的回测开始时间
df = df[df['candle_begin_time'] <= pd.to_datetime(date_end)]  # 筛选时间小于等于我们指定的回测结束时间
df.reset_index(inplace=True, drop=True)  # 重新设置一下index

# === 计算实际持仓
df = position_for_future(df)  # 调用函数，计算实际的持仓

# ===== 计算资金曲线
# === 计算资金曲线
min_amount = min_amount_dict[symbol.replace('-', '')]  # 获取最小下单量
df = cal_equity_curve(df, slippage=slippage, c_rate=c_rate, leverage_rate=leverage_rate,
                      min_amount=min_amount, min_margin_ratio=min_margin_ratio)  # 计算资金曲线
print(df)  # 输出计算资金曲线后的df
print('策略最终收益：', df.iloc[-1]['equity_curve'])  # 输出策略的最终收益，即最后一行的equity_curve
# ==== 输出资金曲线文件
# === 处理数据
df_output = df[
    ['candle_begin_time', 'open', 'high', 'low', 'close', 'signal', 'pos', 'quote_volume',
     'equity_curve']]  # 筛选一下需要的列，避免把所有的列都存在内存中，避免加大内存的压力
df_output.rename(columns={'median': 'line_median', 'upper': 'line_upper', 'lower': 'line_lower',
                          'quote_volume': 'b_bar_quote_volume',
                          'equity_curve': 'r_line_equity_curve'}, inplace=True)  # 对指定列名重命名，方便我们看数据是容易理解
# === 保存文件
df_output.to_csv(
    root_path + '/data/output/equity_curve/%s&%s&%s&%s.csv' % (signal_name, symbol.split('-')[0], rule_type, str(para)),
    index=False, encoding='gbk')  # 以GBK编码并且删除index保存csv文件

# ==== 策略评价
# === 计算每笔交易
trade = transfer_equity_curve_to_trade(df)  # 调用函数，通过带有资金曲线的df计算每笔交易
print('逐笔交易：\n', trade)  # 输出每笔交易

# === 绘制资金曲线
# 拼接资金曲线的图片标题
title = symbol + '_' + str(para)  # 拼接一下资金曲线的图片标题，即币种名称+回测参数
# 绘制资金曲线
draw_equity_curve_mat(df, trade, title)  # 调用函数绘制资金曲线，需要传入带有资金曲线的df、每笔交易数据以及图片的标题

# === 计算各类统计指标
# 计算策略评价指标
r, monthly_return = strategy_evaluate(df, trade)  # 调用函数策略评价指标，需要传入带有资金曲线的df以及每笔交易数据
# 输出策略评价指标数据
print(r)  # 输出策略评价指标
print(monthly_return)  # 输出每月收益率
# === 输出回测使用的时间
print(datetime.now() - start_time)
