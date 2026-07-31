import pandas as pd

df = pd.DataFrame({
    'data': [45.82, -60.90, 70.36, 26.77, 21.53]
})
# print(df)
# REF(data,1)
df['REF'] = df['data'].shift(1)  # 留空默认为1
# print(df)

# IF(data>40,1,0)
df.loc[df['data'] > 40, 'IF'] = 1
df.loc[df['data'] <= 40, 'IF'] = 0
# df['IF'].fillna(value=0, inplace=True)
# print(df)
# SUM(data,2)
df['SUM'] = df['data'].rolling(2, min_periods=1).sum()  # min_periods指定最小窗口
# print(df)

# CUMSUM(data)
df['CUMSUM'] = df['data'].cumsum()  # 会有精度的问题
# print(df)

# MAX(data,2)、MIN(data,2)
df['MAX'] = df['data'].rolling(2, min_periods=1).max()
df['MIN'] = df['data'].rolling(2, min_periods=1).min()
# print(df)

# MAX(data,REF(data,1)、MIN(data,REF(data,1)
df['MAX_'] = df[['data', 'REF']].max(axis=1)  # axis指定计算方式是按照每行
df['MIN_'] = df[['data', 'REF']].min(axis=1)
# print(df)


# ABS(data)
df['ABS'] = abs(df['data'])
# print(df)
# MA(data,2)
df['MA'] = df['data'].rolling(2).mean()
# print(df)


# EMA(data,2)
# 参考文章：https://blog.csdn.net/small__roc/article/details/123482186
df['EMA'] = df['data'].ewm(span=2, min_periods=1, adjust=False).mean()  #
# print(df)
# SMA(data,2,1)
df['SMA'] = df['data'].ewm(alpha=1 / 2, adjust=False).mean()
print(df)
# WMA(data,2)
df['WMA'] = df['data'].rolling(2).apply(lambda x: x[::-1].cumsum().sum() * 2 / 2 / (2 + 1), raw=True)
# print(df)

# DMA(data, 2)
df['DMA'] = df['data'].ewm(alpha=0.2, adjust=False).mean()
# print(df)
