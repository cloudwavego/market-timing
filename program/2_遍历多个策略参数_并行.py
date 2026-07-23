"""
币圈择时小组第2期专属代码
author: 邢不行
微信: xbx9585
"""
import warnings
from datetime import datetime
from datetime import timedelta
from functools import partial
from multiprocessing import Pool, cpu_count

import Signals
from Config import *
from Evaluate import *
from Function import *
from Position import *
from Statistics import *


def calculate_by_one_loop(para, df, signal_name, symbol, rule_type, min_amount):
    """
    回测每个传递进来的数据
    :param para:    回测参数
    :param df:  原始数据
    :param signal_name: 策略名称
    :param symbol:  币种名称
    :param rule_type:   回测时间周期
    :param min_amount:  最小下单量
    :return:
        返回币种的回测结果，包含累积币种名称、净值、年化收益最大回撤、年化收益回撤比字段
    """
    warnings.filterwarnings('ignore')
    # ==== 获取数据
    # === 对原始数据进行copy
    _df = df.copy()  # 先对数据进行copy，避免修改原始数据
    # === 计算交易信号
    _df = getattr(Signals, signal_name)(_df, para=para, proportion=proportion,
                                        leverage_rate=leverage_rate)  # 调用传递过来的signal名称生成signal信号

    # === 对数据进行时间筛选  计算信号后再筛选数据，避免前面几个周期因为数据量不够导致计算结果为空或失真
    # 保留币种上线N天之后的日期
    t = _df.iloc[0]['candle_begin_time'] + timedelta(days=drop_days)  # 获取第一行数据的日期，并且加上我们指定的天数
    _df = _df[_df['candle_begin_time'] > t]  # 筛选时间
    _df = _df[_df['candle_begin_time'] >= pd.to_datetime(date_start)]  # 筛选时间大于等于我们指定的回测开始时间
    _df = _df[_df['candle_begin_time'] <= pd.to_datetime(date_end)]  # 筛选时间小于等于我们指定的回测结束时间
    _df.reset_index(inplace=True, drop=True)  # 重新设置一下index

    # === 计算实际持仓
    _df = position_for_future(_df)  # 调用函数，计算实际的持仓

    # ===== 计算资金曲线
    # === 计算资金曲线
    _df = cal_equity_curve(_df, slippage=slippage, c_rate=c_rate,
                           leverage_rate=leverage_rate,
                           min_amount=min_amount,
                           min_margin_ratio=min_margin_ratio)  # 计算资金曲线
    # ==== 策略评价
    # === 计算每笔交易
    trade = transfer_equity_curve_to_trade(_df)  # 调用函数，通过带有资金曲线的df计算每笔交易
    # 判断每笔交易是否为空，如果为空即为没有触发信号，直接返回空的数据
    if trade.empty:  # 判断trade是否为空
        return pd.DataFrame()  # 返回一个空的df

    # === 计算各类统计指标
    # 计算策略评价指标
    r, monthly_return = strategy_evaluate(_df, trade)  # 调用函数策略评价指标，需要传入带有资金曲线的df以及每笔交易数据
    # 保存策略收益
    rtn = pd.DataFrame()  # 创建一个新的df，用于保存回测的指标数据
    rtn.loc[0, 'para'] = str(para)  # 保存回测的参数
    # 遍历所有计算出来的策略评价指标，进行保存
    for i in r.index:  # 遍历所有的index
        rtn.loc[0, i] = r.loc[i, 0]  # 进行保存
    # 输出一下回测的结果
    print(signal_name, symbol, rule_type, para, '策略收益：', r.loc['累积净值', 0])  # 输出策略名称、币种、回测时间周期、策略的累积净值
    # 返回回测的详情数据
    return rtn


if __name__ == '__main__':
    # ==== 遍历所有的策略
    # 遍历指定的策略
    for signal_name in ['signal_add_bias']:
        # 遍历不同的币种
        for symbol in symbol_list:
            # 获取当前币种的最小下单量
            min_amount = min_amount_dict[symbol.replace('-', '')]  # 获取最小下单量
            # 遍历不同的周期
            for rule_type in ['4H']:
                # ===== 输出一下回测的详情
                print('开始遍历该策略参数：', signal_name, symbol, rule_type)  # 输出当前要回测的策略名称、币种、回测时间周期
                # ==== 读入数据
                # === 读取原始的csv数据
                df = pd.read_csv(os.path.join(symbol_data_path, symbol + '.csv'), encoding='gbk',
                                 parse_dates=['candle_begin_time'],
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

                # === 获取策略参数组合
                para_list = getattr(Signals, signal_name + '_para_list')()  # 根据遍历到的策略名称，获取当前策略的遍历参数

                # === 并行回测
                # 标记开始时间
                start_time = datetime.now()  # 标记开始时间

                # 利用partial指定参数值
                part = partial(calculate_by_one_loop, df=df, signal_name=signal_name, symbol=symbol,
                               rule_type=rule_type, min_amount=min_amount)  # 使用便函数指定所有固定的参数
                multiple_process = True  # 设置是否并行，True为并行，False为串行
                # === 开始进行回测
                if multiple_process:
                    with Pool(max(cpu_count() - 1, 1)) as pool:
                        # 使用并行批量获得data frame的一个列表
                        df_list = pool.map(part, para_list)
                else:
                    df_list = []  # 定义一个空的列表，用来保存回测的结果

                    # 循环每个参数
                    for para in para_list:
                        res_df = calculate_by_one_loop(para=para, df=df, signal_name=signal_name, symbol=symbol,
                                                       rule_type=rule_type, min_amount=min_amount)  # 调用回测的函数，返回回测结果
                        df_list.append(res_df)  # 将回测结果累加到df_list，用于后续合并大表使用

                print('读入完成, 开始合并', datetime.now() - start_time)  # 回测结束，输出一下使用的时间

                # ==== 整理回测后的数据
                # === 将df_list内所有的回测结果合并，作为一个大表，并重新设置一下index
                para_curve_df = pd.concat(df_list, ignore_index=True)  # 合并为一个大的DataFrame

                # ==== 读取基准数据，即从回测开始持有到回测结束的结果
                # 拼接一下基本数据的路径
                p = root_path + '/data/output/para/基准&%s&%s.csv' % (leverage_rate, rule_type)  # 拼接数据保存的路径
                original = pd.read_csv(p, encoding='gbk')  # 以GBK编码读取基本数据的csv文件
                # ==== 合并基准数据
                para_curve_df['币种原始累积净值'] = original.loc[original['币种'] == symbol].iloc[0][
                    '累积净值']  # 合并基准累积净值
                para_curve_df['币种原始年化收益'] = original.loc[original['币种'] == symbol].iloc[0][
                    '年化收益']  # 合并基准年化收益
                para_curve_df['币种原始最大回撤'] = original.loc[original['币种'] == symbol].iloc[0][
                    '最大回撤']  # 合并基准最大回撤
                para_curve_df['币种原始年化收益/回撤比'] = original.loc[original['币种'] == symbol].iloc[0][
                    '年化收益/回撤比']  # 合并基准年化收益回撤比

                # ==== 整理回测后的数据
                # === 对数据进行排序
                para_curve_df.sort_values(by='年化收益/回撤比', ascending=False, inplace=True)  # 将数据根据年化收益回撤比降序排序
                print(para_curve_df.head(10))  # 输出前10行数据

                # === 保存回测后的结果
                p = root_path + '/data/output/para/%s&%s&%s&%s.csv' % (
                    signal_name, symbol, leverage_rate, rule_type)  # 拼接数据保存的路径

                para_curve_df.to_csv(p, index=False, mode='w', encoding='gbk')  # 以GBK编码并且删除index保存csv文件
                # ==== 输出一下本轮回测使用的时间
                print(datetime.now() - start_time)  # 输出回测时间
