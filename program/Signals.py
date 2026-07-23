"""
币圈择时小组第2期专属代码
author: 邢不行
微信: xbx9585
"""
from Function import *


# === 简单布林策略
# 策略
def signal_simple_bolling(df, para=[200, 2], proportion=1, leverage_rate=1):
    """
    :param df: 原始数据
    :param para: n, m   siganl计算的参数
    :return:
        返回包含signal的数据

    # 布林线策略
    # 布林线中轨：n天收盘价的移动平均线
    # 布林线上轨：n天收盘价的移动平均线 + m * n天收盘价的标准差
    # 布林线上轨：n天收盘价的移动平均线 - m * n天收盘价的标准差
    # 当收盘价由下向上穿过上轨的时候，做多；然后由上向下穿过中轨的时候，平仓。
    # 当收盘价由上向下穿过下轨的时候，做空；然后由下向上穿过中轨的时候，平仓。
    """

    # ===== 获取策略参数
    n = int(para[0])  # 获取参数n，即para第一个元素
    m = para[1]  # 获取参数m，即para第二个元素

    # ===== 计算指标
    # 计算均线
    df['median'] = df['close'].rolling(n, min_periods=1).mean()  # 计算收盘价n个周期的均线，如果K线数据小于n就用K线的数量进行计算
    # 计算上轨、下轨道
    df['std'] = df['close'].rolling(n, min_periods=1).std(ddof=0)  # 计算收盘价n日的std，ddof代表标准差自由度
    df['upper'] = df['median'] + m * df['std']  # 计算上轨
    df['lower'] = df['median'] - m * df['std']  # 计算下轨

    # ===== 找出交易信号
    # === 找出做多信号
    condition1 = df['close'] > df['upper']  # 当前K线的收盘价 > 上轨
    condition2 = df['close'].shift(1) <= df['upper'].shift(1)  # 之前K线的收盘价 <= 上轨
    df.loc[condition1 & condition2, 'signal_long'] = 1  # 将产生做多信号的那根K线的signal设置为1，1代表做多

    # === 找出做多平仓信号
    condition1 = df['close'] < df['median']  # 当前K线的收盘价 < 中轨
    condition2 = df['close'].shift(1) >= df['median'].shift(1)  # 之前K线的收盘价 >= 中轨
    df.loc[condition1 & condition2, 'signal_long'] = 0  # 将产生平仓信号当天的signal设置为0，0代表平仓

    # === 找出做空信号
    condition1 = df['close'] < df['lower']  # 当前K线的收盘价 < 下轨
    condition2 = df['close'].shift(1) >= df['lower'].shift(1)  # 之前K线的收盘价 >= 下轨
    df.loc[condition1 & condition2, 'signal_short'] = -1  # 将产生做空信号的那根K线的signal设置为-1，-1代表做空

    # === 找出做空平仓信号
    condition1 = df['close'] > df['median']  # 当前K线的收盘价 > 中轨
    condition2 = df['close'].shift(1) <= df['median'].shift(1)  # 之前K线的收盘价 <= 中轨
    df.loc[condition1 & condition2, 'signal_short'] = 0  # 将产生平仓信号当天的signal设置为0，0代表平仓

    # ===== 合并做多做空信号，去除重复信号
    # === 合并做多做空信号
    df['signal'] = df[['signal_long', 'signal_short']].sum(axis=1, min_count=1,
                                                           skipna=True)  # 合并多空信号，即signal_long与signal_short相加，得到真实的交易信号
    # === 去除重复信号
    temp = df[df['signal'].notnull()][['signal']]  # 筛选siganla不为空的数据，并另存一个变量
    temp = temp[temp['signal'] != temp['signal'].shift(1)]  # 筛选出当前周期与上个周期持仓信号不一致的，即去除重复信号
    df['signal'] = temp['signal']  # 将处理后的signal覆盖到原始数据的signal列

    # ===== 删除无关变量
    df.drop(['std', 'signal_long', 'signal_short'], axis=1, inplace=True)  # 删除std、signal_long、signal_short列

    # ===== 止盈止损
    # 校验当前的交易是否需要进行止盈止损
    df = process_stop_loss_close(df, proportion, leverage_rate=leverage_rate)  # 调用函数，判断是否需要止盈止损，df需包含signal列

    return df


# 策略参数组合
def signal_simple_bolling_para_list(m_list=range(20, 1000 + 20, 20),
                                    n_list=[i / 10 for i in list(np.arange(3, 50 + 2, 2))]):
    """
    产生布林 策略的参数范围
    :param m_list:  m值的列表
    :param n_list:  n值的列表
    :return:
        返回一个大的列表，格式为：[[20, 0.3]]
    """
    # ==== 输出一下参数的范围
    print('参数遍历范围：')
    print('m_list', list(m_list))  # 输出m的遍历范围
    print('n_list', list(n_list))  # 输出n的遍历范围

    # ===== 构建遍历的列表
    para_list = []  # 定义一个新的列表，用于存储遍历参数

    # === 遍历参数
    for m in m_list:  # 遍历m的参数
        for n in n_list:  # 遍历n的参数
            para = [m, n]  # 构建每个遍历列表的每个参数
            para_list.append(para)  # 将参数累加到para_list
    # ===== 返回参数列表
    return para_list


# =====作者邢不行
# 策略
def signal_xingbuxing(df, para=[200, 2, 0.05], proportion=1, leverage_rate=1):
    """
    针对原始布林策略进行修改。
    bias = close / 均线 - 1
    当开仓的时候，如果bias过大，即价格离均线过远，那么就先不开仓。等价格和均线距离小于bias_pct之后，才按照原计划开仓
    :param df: 原始数据
    :param para: n,m,bias_pct siganl计算的参数
    :return:
    """

    # ===== 获取策略参数
    n = int(para[0])  # 获取参数n，即para第一个元素
    m = float(para[1])  # 获取参数m，即para第二个元素
    bias_pct = float(para[2])  # 获取参数bias_pct，即para第三个元素

    # ===== 计算指标
    # 计算均线
    df['median'] = df['close'].rolling(n, min_periods=1).mean()  # 计算收盘价n个周期的均线，如果K线数据小于n就用K线的数量进行计算
    # 计算上轨、下轨道
    df['std'] = df['close'].rolling(n, min_periods=1).std(ddof=0)  # 计算收盘价n日的std，ddof代表标准差自由度
    df['upper'] = df['median'] + m * df['std']  # 计算上轨
    df['lower'] = df['median'] - m * df['std']  # 计算下轨
    # 计算bias
    df['bias'] = df['close'] / df['median'] - 1

    # ===== 找出交易信号
    # === 找出做多信号
    condition1 = df['close'] > df['upper']  # 当前K线的收盘价 > 上轨
    condition2 = df['close'].shift(1) <= df['upper'].shift(1)  # 之前K线的收盘价 <= 上轨
    df.loc[condition1 & condition2, 'signal_long'] = 1  # 将产生做多信号的那根K线的signal设置为1，1代表做多

    # === 找出做多平仓信号
    condition1 = df['close'] < df['median']  # 当前K线的收盘价 < 中轨
    condition2 = df['close'].shift(1) >= df['median'].shift(1)  # 之前K线的收盘价 >= 中轨
    df.loc[condition1 & condition2, 'signal_long'] = 0  # 将产生平仓信号当天的signal设置为0，0代表平仓

    # === 找出做空信号
    condition1 = df['close'] < df['lower']  # 当前K线的收盘价 < 下轨
    condition2 = df['close'].shift(1) >= df['lower'].shift(1)  # 之前K线的收盘价 >= 下轨
    df.loc[condition1 & condition2, 'signal_short'] = -1  # 将产生做空信号的那根K线的signal设置为-1，-1代表做空

    # === 找出做空平仓信号
    condition1 = df['close'] > df['median']  # 当前K线的收盘价 > 中轨
    condition2 = df['close'].shift(1) <= df['median'].shift(1)  # 之前K线的收盘价 <= 中轨
    df.loc[condition1 & condition2, 'signal_short'] = 0  # 将产生平仓信号当天的signal设置为0，0代表平仓

    # ===== 合并做多做空信号
    df['signal'] = df[['signal_long', 'signal_short']].sum(axis=1, min_count=1,
                                                           skipna=True)  # 合并多空信号，即signal_long与signal_short相加，得到真实的交易信号

    # ===== 根据bias，修改开仓时间
    df['temp'] = df['signal']
    # === 将原始信号做多时，当bias大于阀值，设置为空
    condition1 = (df['signal'] == 1)  # signal为1
    condition2 = (df['bias'] > bias_pct)  # bias大于bias_pct
    df.loc[condition1 & condition2, 'temp'] = None  # 将signal设置为空

    # === 将原始信号做空时，当bias大于阀值，设置为空
    condition1 = (df['signal'] == -1)  # signal为-1
    condition2 = (df['bias'] < -1 * bias_pct)  # bias小于 (-1 * bias_pct)
    df.loc[condition1 & condition2, 'temp'] = None  # 将signal设置为空

    # 原始信号刚开仓，并且大于阀值，将信号设置为0
    condition1 = (df['signal'] != df['signal'].shift(1))
    condition2 = (df['temp'].isnull())
    df.loc[condition1 & condition2, 'temp'] = 0

    # ===== 合去除重复信号
    # === 去除重复信号
    df['signal'] = df['temp']
    temp = df[df['signal'].notnull()][['signal']]  # 筛选siganla不为空的数据，并另存一个变量
    temp = temp[temp['signal'] != temp['signal'].shift(1)]  # 筛选出当前周期与上个周期持仓信号不一致的，即去除重复信号
    df['signal'] = temp['signal']  # 将处理后的signal覆盖到原始数据的signal列

    # ===== 删除无关变量
    df.drop(['raw_signal', 'median', 'std', 'upper', 'lower', 'bias', 'temp', 'signal_long', 'signal_short'], axis=1,
            inplace=True)  # 删除raw_signal、median、std、upper、lower、bias、temp、signal_long、signal_short列

    # ===== 止盈止损
    # 校验当前的交易是否需要进行止盈止损
    df = process_stop_loss_close(df, proportion, leverage_rate=leverage_rate)  # 调用函数，判断是否需要止盈止损，df需包含signal列

    return df


# 策略参数组合
def signal_xingbuxing_para_list(m_list=range(20, 1000 + 20, 20), n_list=[i / 10 for i in list(np.arange(3, 50 + 2, 2))],
                                bias_pct_list=[i / 100 for i in list(np.arange(5, 20 + 2, 2))]):
    """
    :param m_list: m值的列表
    :param n_list: n值的列表
    :param bias_pct_list: bias_pct值的列表
    :return:
        返回一个大的列表，格式为：[[20, 0.3, 0.05]]
    """
    # ==== 输出一下参数的范围
    print('参数遍历范围：')
    print('m_list', list(m_list))  # 输出m的遍历范围
    print('n_list', list(n_list))  # 输出n的遍历范围
    print('bias_pct_list', list(bias_pct_list))  # 输出bias_pct的遍历范围

    # ===== 构建遍历的列表
    para_list = []  # 定义一个新的列表，用于存储遍历参数

    # === 遍历参数
    for bias_pct in bias_pct_list:  # 遍历bias_pct的参数
        for m in m_list:  # 遍历m的参数
            for n in n_list:  # 遍历n的参数
                para = [m, n, bias_pct]  # 构建每个遍历列表的每个参数
                para_list.append(para)  # 将参数累加到para_list
    # ===== 返回参数列表
    return para_list


def signal_add_bias(df, para=[20, 0.05], proportion=1, leverage_rate=1):
    """

    :param df: 原始数据
    :param para: siganl计算的参数
    :param proportion: 止损比例
    :param leverage_rate: 杠杆倍数
    :return:
    """
    # ===== 获取策略参数
    n = para[0]  # 获取参数n，即para第一个元素
    bias_pct = float(para[1])  # 获取参数bias_pct，即para第二个元素

    # ===== 计算指标
    # 计算均线
    df['median'] = df['close'].rolling(n, min_periods=1).mean()  # 计算收盘价n个周期的均线，如果K线数据小于n就用K线的数量进行计算
    df['bias'] = df['close'] / df['median'] - 1  # 计算bias

    df['TYP'] = (df['high'] + df['low'] + df['close']) / 3  # 计算TYP
    df['H'] = np.where(df['high'] - df['TYP'].shift(1) > 0, df['high'] - df['TYP'].shift(1), 0)  # 计算H
    df['L'] = np.where(df['TYP'].shift(1) - df['low'] > 0, df['TYP'].shift(1) - df['low'], 0)  # 计算L
    df['Cr_%s' % (n)] = df['H'].rolling(n).sum() / df['L'].rolling(n, min_periods=1).sum() * 100  # 计算CR因子

    # ===== 找出交易信号
    # === 找出做多信号 CR 上穿 200
    condition1 = df['Cr_%s' % str(n)] > 200  # 当前周期CR大于200
    condition2 = df['Cr_%s' % str(n)].shift() <= 200  # 上个周期CR小于等于200
    df.loc[condition1 & condition2, 'signal_long'] = 1  # 1代表做多

    # === 找出做空信号 CR 下穿 50
    condition1 = df['Cr_%s' % str(n)] < 50  # 当前周期CR小于50
    condition2 = df['Cr_%s' % str(n)].shift() >= 50  # 上个周期CR大于等于50
    df.loc[condition1 & condition2, 'signal_short'] = -1  # -1代表做空

    # ===== 合并做多做空信号，去除重复信号
    # === 合并做多做空信号
    df['signal'] = df[['signal_long', 'signal_short']].sum(axis=1, min_count=1,
                                                           skipna=True)  # 合并多空信号，即signal_long与signal_short相加，得到真实的交易信号
    # === 去除重复信号
    temp = df[df['signal'].notnull()][['signal']]  # 筛选siganla不为空的数据，并另存一个变量
    temp = temp[temp['signal'] != temp['signal'].shift(1)]  # 筛选出当前周期与上个周期持仓信号不一致的，即去除重复信号
    df['signal'] = temp['signal']  # 将处理后的signal覆盖到原始数据的signal列

    # ===== 根据bias，修改开仓时间
    df['temp'] = df['signal']

    # === 将原始信号做多时，当bias大于阀值，设置为空
    condition1 = (df['signal'] == 1)  # signal为1
    condition2 = (df['bias'] > bias_pct)  # bias大于bias_pct
    df.loc[condition1 & condition2, 'temp'] = None  # 将signal设置为空

    # === 将原始信号做空时，当bias小于阀值，设置为空
    condition1 = (df['signal'] == -1)  # signal为-1
    condition2 = (df['bias'] < -1 * bias_pct)  # bias小于 (-1 * bias_pct)
    df.loc[condition1 & condition2, 'temp'] = None  # 将signal设置为空
    df['signal'] = df['temp']

    # ===== 止盈止损
    # 校验当前的交易是否需要进行止盈止损
    df = process_stop_loss_close(df, proportion, leverage_rate=leverage_rate)  # 调用函数，判断是否需要止盈止损，df需包含signal列

    return df


def signal_add_bias_para_list(n_list=generate_fibonacci_sequence(2, 100),
                              bias_pct_list=generate_fibonacci_sequence(1, 100)):
    """

    :param n_list: N值的列表
    :param bias_pct_list:  bias_pct值的列表
    :return:
    """
    # ===== 构建遍历的列表
    para = []  # 定义一个新的列表，用于存储遍历参数

    # === 遍历参数
    for n in n_list:  # 遍历n的参数
        for bias_pct in bias_pct_list:  # 遍历bias_pct的参数
            bias_pct = bias_pct / 100  # 调整bias_pct参数的值
            para.append([int(n), bias_pct])  # 将参数累加到para_list
    # ===== 返回参数列表
    return para


def signal_imi(df, para=14, proportion=1, leverage_rate=1):
    """

    :param df:
    :param para:
    :param proportion:
    :param leverage_rate:
    :return:
    """
    # ===== 获取策略参数
    n = para  # 获取参数n

    # ===== 计算指标
    # === 计算one_day_INC
    # SUM(IF(CLOSE>OPEN,CLOSE-OPEN,0),N)
    # 如果某一列为空值，那么相减计算出来的也是空值
    df.loc[df['close'] > df['open'], 'one_day_INC'] = df['close'] - df['open']  # 如果收盘价大于开盘价，one_day_INC取收盘价与开盘价的差值
    df.loc[df['close'] <= df['open'], 'one_day_INC'] = 0  # 如果收盘价小于等于开盘价，one_day_INC取0

    # === 计算INC
    df['INC'] = df['one_day_INC'].rolling(n, min_periods=1).sum()  # 计算INC，即n个周期one_day_INC的和

    # === 计算one_day_DEC
    # SUM(IF(OPEN>CLOSE,OPEN-CLOSE,0),N)
    df.loc[df['open'] > df['close'], 'one_day_DEC'] = df['open'] - df['close']  # 如果开盘价大于收盘价，one_day_DEC取开盘价与收盘价的差值
    df.loc[df['open'] <= df['close'], 'one_day_DEC'] = 0  # 如果开盘价小于等于收盘价，one_day_DEC取0

    # === 计算DEC
    df['DEC'] = df['one_day_DEC'].rolling(n, min_periods=1).sum()  # 计算DEC，即n个周期one_day_DEC的和

    # === 计算IMI
    # IMI=INC/(INC+DEC)
    df['IMI'] = df['INC'] / (df['INC'] + df['DEC']) * 100  # 计算IMD，即INC / (INC + DEC) * 100

    # ===== 找出交易信号
    # === 找出做多信号
    condition = df['IMI'] > 80  # IMI大于80
    condition &= df['IMI'].shift() <= 80  # 上个周期的IMI小于等于80
    df.loc[condition, 'signal_long'] = 1  # 将产生做多信号的那根K线的signal设置为1，1代表做多

    # === 找出做空信号
    condition = df['IMI'] < 20  # IMI小于20
    condition &= df['IMI'].shift() >= 20  # 上个周期的IMI大于等于20
    df.loc[condition, 'signal_short'] = -1  # 将产生做空信号的那根K线的signal设置为-1，-1代表做空

    # ========================= 固定代码 =========================

    # ===== 合并做多做空信号，去除重复信号
    # === 合并做多做空信号
    df['signal'] = df[['signal_long', 'signal_short']].sum(axis=1, min_count=1,
                                                           skipna=True)  # 合并多空信号，即signal_long与signal_short相加，得到真实的交易信号

    # === 去除重复信号
    temp = df[df['signal'].notnull()][['signal']]  # 筛选siganla不为空的数据，并另存一个变量
    temp = temp[temp['signal'] != temp['signal'].shift(1)]  # 筛选出当前周期与上个周期持仓信号不一致的，即去除重复信号
    df['signal'] = temp['signal']  # 将处理后的signal覆盖到原始数据的signal列

    # ========================= 固定代码 =========================

    # ===== 删除无关变量
    df.drop(['INC', 'DEC', 'IMI', 'signal_long', 'signal_short'], axis=1,
            inplace=True)  # 删除INC、DEC、IMI、signal_long、signal_short列

    # ===== 止盈止损
    # 校验当前的交易是否需要进行止盈止损
    df = process_stop_loss_close(df, proportion, leverage_rate=leverage_rate)  # 调用函数，判断是否需要止盈止损，df需包含signal列

    return df


def signal_imi_para_list(n_list=generate_fibonacci_sequence(2, 100)):
    """

    :param n_list: n值的列表
    :return:
    """
    # ===== 构建遍历的列表
    para_list = []  # 定义一个新的列表，用于存储遍历参数

    # === 遍历参数
    for n in n_list:  # 遍历n的参数
        para_list.append(int(n))  # 将参数累加到para_list

    # ===== 返回参数列表
    return para_list
    """
    布林+RSI策略
    :param df: 原始数据
    :param para: siganl计算的参数：布林的n, m，rsi的天数
    :return:
        返回包含signal的数据
    """

    # ===== 获取策略参数
    n = int(para[0])  # 获取参数n，即para第一个元素
    m = para[1]  # 获取参数m，即para第二个元素
    window = int(para[2])

    # ===== 计算指标
    # 计算均线
    df['median'] = df['close'].rolling(n, min_periods=1).mean()  # 计算收盘价n个周期的均线，如果K线数据小于n就用K线的数量进行计算
    # 计算上轨、下轨道
    df['std'] = df['close'].rolling(n, min_periods=1).std(ddof=0)  # 计算收盘价n日的std，ddof代表标准差自由度
    df['upper'] = df['median'] + m * df['std']  # 计算上轨
    df['lower'] = df['median'] - m * df['std']  # 计算下轨

    # 计算RSI： N日RSI = A /（A + B）×100
    # A = N日内收盘涨幅之和
    # B = N日内收盘跌幅之和（取正值）
    # 计算价格变化
    delta = df['close'].diff()
    # 将涨跌幅分为正变化和负变化
    gain = delta.where(delta > 0, 0)
    loss = -delta.where(delta < 0, 0)
    # 计算平均涨幅和平均跌幅
    avg_gain = gain.rolling(window=window, min_periods=1).mean()
    avg_loss = loss.rolling(window=window, min_periods=1).mean()
    # 计算RS值
    rs = avg_gain / avg_loss
    # 计算RSI值
    df['rsi'] = 100 - (100 / (1 + rs))

    # ===== 找出交易信号
    # === 找出做多信号
    # 价格高于上轨，RSI高于75，多投，损益比1：1.5-2
    condition1 = df['close'] > df['upper']  # 当前K线的收盘价 > 上轨
    condition2 = df['close'].shift(1) <= df['upper'].shift(1)  # 之前K线的收盘价 <= 上轨
    condition3 = df['rsi'] >= 75
    df.loc[condition1 & condition2 & condition3, 'signal_long'] = 1  # 将产生做多信号的那根K线的signal设置为1，1代表做多

    # === 找出做多平仓信号
    condition1 = df['close'] < df['median']  # 当前K线的收盘价 < 中轨
    condition2 = df['close'].shift(1) >= df['median'].shift(1)  # 之前K线的收盘价 >= 中轨
    df.loc[condition1 & condition2, 'signal_long'] = 0  # 将产生平仓信号当天的signal设置为0，0代表平仓

    # === 找出做空信号
    # 价格低于下轨且RSI低于25，空投，损益比1：1.5-2
    condition1 = df['close'] < df['lower']  # 当前K线的收盘价 < 下轨
    condition2 = df['close'].shift(1) >= df['lower'].shift(1)  # 之前K线的收盘价 >= 下轨
    condition3 = df['rsi'] <= 25
    df.loc[condition1 & condition2 & condition3, 'signal_short'] = -1  # 将产生做空信号的那根K线的signal设置为-1，-1代表做空

    # === 找出做空平仓信号
    condition1 = df['close'] > df['median']  # 当前K线的收盘价 > 中轨
    condition2 = df['close'].shift(1) <= df['median'].shift(1)  # 之前K线的收盘价 <= 中轨
    df.loc[condition1 & condition2, 'signal_short'] = 0  # 将产生平仓信号当天的signal设置为0，0代表平仓

    # ===== 合并做多做空信号，去除重复信号
    # === 合并做多做空信号
    df['signal'] = df[['signal_long', 'signal_short']].sum(axis=1, min_count=1,
                                                           skipna=True)  # 合并多空信号，即signal_long与signal_short相加，得到真实的交易信号
    # === 去除重复信号
    temp = df[df['signal'].notnull()][['signal']]  # 筛选siganla不为空的数据，并另存一个变量
    temp = temp[temp['signal'] != temp['signal'].shift(1)]  # 筛选出当前周期与上个周期持仓信号不一致的，即去除重复信号
    df['signal'] = temp['signal']  # 将处理后的signal覆盖到原始数据的signal列

    # ===== 删除无关变量
    df.drop(['std', 'signal_long', 'signal_short'], axis=1, inplace=True)  # 删除std、signal_long、signal_short列

    # ===== 止盈止损
    # 校验当前的交易是否需要进行止盈止损
    df = process_stop_loss_close(df, proportion, leverage_rate=leverage_rate)  # 调用函数，判断是否需要止盈止损，df需包含signal列

    return df

def signal_bolling_rsi(df, para=[200, 2, 13], proportion=1, leverage_rate=1):
    """
    布林+RSI策略
    :param df: 原始数据
    :param para: siganl计算的参数：布林的n, m，rsi的天数
    :return:
        返回包含signal的数据
    """

    # ===== 获取策略参数
    n = int(para[0])  # 获取参数n，即para第一个元素
    m = para[1]  # 获取参数m，即para第二个元素
    window = int(para[2])

    # ===== 计算指标
    # 计算均线
    df['median'] = df['close'].rolling(n, min_periods=1).mean()  # 计算收盘价n个周期的均线，如果K线数据小于n就用K线的数量进行计算
    # 计算上轨、下轨道
    df['std'] = df['close'].rolling(n, min_periods=1).std(ddof=0)  # 计算收盘价n日的std，ddof代表标准差自由度
    df['upper'] = df['median'] + m * df['std']  # 计算上轨
    df['lower'] = df['median'] - m * df['std']  # 计算下轨

    # 计算RSI： N日RSI = A /（A + B）×100
    # A = N日内收盘涨幅之和
    # B = N日内收盘跌幅之和（取正值）
    # 计算价格变化
    delta = df['close'].diff()
    # 将涨跌幅分为正变化和负变化
    gain = delta.where(delta > 0, 0)
    loss = -delta.where(delta < 0, 0)
    # 计算平均涨幅和平均跌幅
    avg_gain = gain.rolling(window=window, min_periods=1).mean()
    avg_loss = loss.rolling(window=window, min_periods=1).mean()
    # 计算RS值
    rs = avg_gain / avg_loss
    # 计算RSI值
    df['rsi'] = 100 - (100 / (1 + rs))

    # ===== 找出交易信号
    # === 找出做多信号
    # 价格高于上轨，RSI高于75，多投，损益比1：1.5-2
    condition1 = df['close'] > df['upper']  # 当前K线的收盘价 > 上轨
    condition2 = df['close'].shift(1) <= df['upper'].shift(1)  # 之前K线的收盘价 <= 上轨
    condition3 = df['rsi'] >= 75
    df.loc[condition1 & condition2 & condition3, 'signal_long'] = 1  # 将产生做多信号的那根K线的signal设置为1，1代表做多

    # === 找出做多平仓信号
    condition1 = df['close'] < df['median']  # 当前K线的收盘价 < 中轨
    condition2 = df['close'].shift(1) >= df['median'].shift(1)  # 之前K线的收盘价 >= 中轨
    df.loc[condition1 & condition2, 'signal_long'] = 0  # 将产生平仓信号当天的signal设置为0，0代表平仓

    # === 找出做空信号
    # 价格低于下轨且RSI低于25，空投，损益比1：1.5-2
    condition1 = df['close'] < df['lower']  # 当前K线的收盘价 < 下轨
    condition2 = df['close'].shift(1) >= df['lower'].shift(1)  # 之前K线的收盘价 >= 下轨
    condition3 = df['rsi'] <= 25
    df.loc[condition1 & condition2 & condition3, 'signal_short'] = -1  # 将产生做空信号的那根K线的signal设置为-1，-1代表做空

    # === 找出做空平仓信号
    condition1 = df['close'] > df['median']  # 当前K线的收盘价 > 中轨
    condition2 = df['close'].shift(1) <= df['median'].shift(1)  # 之前K线的收盘价 <= 中轨
    df.loc[condition1 & condition2, 'signal_short'] = 0  # 将产生平仓信号当天的signal设置为0，0代表平仓

    # ===== 合并做多做空信号，去除重复信号
    # === 合并做多做空信号
    df['signal'] = df[['signal_long', 'signal_short']].sum(axis=1, min_count=1,
                                                           skipna=True)  # 合并多空信号，即signal_long与signal_short相加，得到真实的交易信号
    # === 去除重复信号
    temp = df[df['signal'].notnull()][['signal']]  # 筛选siganla不为空的数据，并另存一个变量
    temp = temp[temp['signal'] != temp['signal'].shift(1)]  # 筛选出当前周期与上个周期持仓信号不一致的，即去除重复信号
    df['signal'] = temp['signal']  # 将处理后的signal覆盖到原始数据的signal列

    # ===== 删除无关变量
    df.drop(['std', 'signal_long', 'signal_short'], axis=1, inplace=True)  # 删除std、signal_long、signal_short列

    # ===== 止盈止损
    # 校验当前的交易是否需要进行止盈止损
    df = process_stop_loss_close(df, proportion, leverage_rate=leverage_rate)  # 调用函数，判断是否需要止盈止损，df需包含signal列

    return df


def signal_bolling_rsi_para_list(m_list=range(20, 1000 + 20, 20), n_list=[i / 10 for i in list(np.arange(3, 50 + 2, 2))],
                                window_list=range(20, 1000 + 20, 20)):
    """
    :param m_list: m值的列表
    :param n_list: n值的列表
    :param window_list: rsi值的列表
    :return:
        返回一个大的列表，格式为：[[20, 0.3, 0.05]]
    """
    # ==== 输出一下参数的范围
    print('参数遍历范围：')
    print('m_list', list(m_list))  # 输出m的遍历范围
    print('n_list', list(n_list))  # 输出n的遍历范围
    print('window_list', list(window_list))  # 输出bias_pct的遍历范围

    # ===== 构建遍历的列表
    para_list = []  # 定义一个新的列表，用于存储遍历参数

    # === 遍历参数
    for window in window_list:  # 遍历bias_pct的参数
        for m in m_list:  # 遍历m的参数
            for n in n_list:  # 遍历n的参数
                para = [m, n, window]  # 构建每个遍历列表的每个参数
                para_list.append(para)  # 将参数累加到para_list
    # ===== 返回参数列表
    return para_list


