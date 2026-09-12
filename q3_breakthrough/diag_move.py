"""诊断：把 Astra 的移动分解为『清目标期间』与『清完后的覆盖收尾』。"""
import random
from benchmark import Fixture, PublicClient
from strategy import Strategy as Astra
from strategy_fast import Strategy as Fast
from strategy_hybrid import Strategy as Hybrid
from geometry import dist

for seed in (1, 6, 12):
    count = 10 + random.Random(seed + 891).randrange(7)
    print('=== seed %d  n=%d ===' % (seed, count))
    for name, cls in (('astra', Astra), ('hybrid', Hybrid)):
        fx = Fixture(seed, count, 'random')
        cl = PublicClient(fx)
        st = cls(cl)
        r = st.run()
        tr = st.trace
        # 找最后一次成功清除的位置
        last_clear = -1
        for i, row in enumerate(tr):
            if row['kind'] == 'clear' and row['response'].get('clear_result') == 'success':
                last_clear = i
        pos = (0.0, 0.0)
        d_main = d_tail = 0.0
        m_main = m_tail = 0
        longest = 0.0
        for i, row in enumerate(tr):
            q = (row['x'], row['y'])
            dd = dist(pos, q)
            longest = max(longest, dd)
            if i <= last_clear:
                d_main += dd
                if row['kind'] == 'measure':
                    m_main += 1
            else:
                d_tail += dd
                if row['kind'] == 'measure':
                    m_tail += 1
            pos = q
        print('  %-6s 总%.1fkm 主体%.1fkm 收尾%.1fkm | 检测 主体%d 收尾%d | 单次最长移动 %.0fm'
              % (name, (d_main + d_tail) / 1000, d_main / 1000, d_tail / 1000,
                 m_main, m_tail, longest))

