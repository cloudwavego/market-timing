import glob
import inspect

import numpy as np

import Signals
from Config import *
from Evaluate import *
from Function import write_file, num_to_pct

pd.set_option('expand_frame_repr', False)  # 当列太多时不换行

# 遍历所有策略结果

# === 获取所有指定策略的遍历结果
path_list = glob.glob(root_path + '/data/output/para/%s*.csv' % signal_name)  # python自带的库，或者某文件夹中所有csv文件的路径
df_list = []
# 遍历读取不同的策略结果
for path in path_list:
    # 读取最优参数，选择排名前strategy_num的
    df = pd.read_csv(path, encoding='gbk')
    df.replace(np.inf, -1, inplace=True)
    df = df.sort_values(by='年化收益/回撤比', ascending=False).head(1)
    df['strategy_name'] = path.split('/')[-1].split('&')[0]
    filename = path.split('/')[-1][:-4]
    df['symbol'] = filename.split('&')[1]
    df['leverage'] = filename.split('&')[2]
    df['周期'] = filename.split('&')[3]
    df_list.append(df)

# 合并所有币种的遍历结果
rtn = pd.concat(df_list)
rtn.reset_index(inplace=True, drop=False)
# === 对一些列进行处理
rtn['最大回撤'] = rtn['最大回撤'].apply(lambda x: float(x[:-1]) / 100)
rtn['币种原始最大回撤'] = rtn['币种原始最大回撤'].apply(lambda x: float(x[:-1]) / 100)
rtn['年化收益'] = rtn['年化收益'].apply(lambda x: float(x[:-1]))
rtn['币种原始年化收益'] = rtn['币种原始年化收益'].apply(lambda x: float(x[:-1]))

# 把合并的数据根据年化收益回撤比排序
rtn.sort_values('年化收益/回撤比', inplace=True, ascending=False)
all_symbol_rtn = rtn[['strategy_name', 'symbol', '周期', 'leverage', 'para', '累积净值', '年化收益', '最大回撤',
                      '年化收益/回撤比']]
print(all_symbol_rtn)
evaluate = pd.DataFrame()

# 计算对应指标的胜率、均值、分位数
for n in ['年化收益', '最大回撤', '年化收益/回撤比']:
    # 50 40 40 /50
    evaluate.loc['胜率', '%s' % n] = rtn[rtn[n] > rtn['币种原始' + n]].shape[0] / rtn.shape[0]
    evaluate_describe_df = (rtn[n] - rtn['币种原始' + n]).describe()
    for i in ['mean', 'std', '25%', '50%', '75%']:
        evaluate.loc[i + '超额', n] = evaluate_describe_df[i]
# 转化为小数
evaluate['年化收益'] = evaluate['年化收益'].apply(num_to_pct)
evaluate['最大回撤'] = evaluate['最大回撤'].apply(num_to_pct)

print(evaluate)

rtn['年化收益/回撤比_超额'] = rtn['年化收益/回撤比'] - rtn['币种原始年化收益/回撤比']
draw_chart_list = [
    '年化收益/回撤比', '年化收益/回撤比_超额'
]
# 绘制分布图
draw_chart_mat(rtn, draw_chart_list)

# ========================= 生成发帖文件 =========================
signal_code = inspect.getsource(getattr(Signals, signal_name))
signal_list_code = inspect.getsource(getattr(Signals, signal_name + '_para_list'))

with open(root_path + '/program/发帖内容/发帖模板.md', 'r', encoding='utf8') as file:
    template = file.read()
    template = template.format(signal_code=signal_code, signal_list_code=signal_list_code,
                               all_symbol_rtn=all_symbol_rtn.to_markdown(index=False), evaluate=evaluate.to_markdown(),
                               proportion=proportion, signal_name=signal_name, rule_type=rule_type,
                               leverage_rate=leverage_rate, date_start=date_start, date_end=date_end)
    write_file(template, os.path.join(root_path, 'program/发帖内容/发帖文件.md'))

# ========================= 生成发帖文件 =========================
