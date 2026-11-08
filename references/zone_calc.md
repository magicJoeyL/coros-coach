# Heart Rate Zone Calculation & COROS EvoLab Alignment

## Three Standard Calculation Methods

| Method | Formula | Best for | Notes |
|--------|---------|----------|-------|
| **HRR (Heart Rate Reserve)** | (MaxHR - RestHR) × % + RestHR | Daniels standard 5-zone | most individualised for aerobic boundaries |
| **LT% (Lactate Threshold %)** | LT HR × % | highest training precision | **COROS EvoLab default standard**; needs measured LT |
| **MaxHR% (Max Heart Rate %)** | MaxHR × % | simplest | least accurate, high individual variance |

---

## 1. Daniels Standard 5-Zone HRR Distribution

| Zone | HRR% | Physiology | Purpose |
|------|------|------------|---------|
| **Z1** | 50-60% | Recovery | warm-up, cool-down, active recovery |
| **Z2** | 60-75% | Aerobic base | easy runs (E), long runs (L), fat metabolism |
| **Z3** | 75-82% | Aerobic threshold | tempo edge, steady-state moderate, marathon pace (M) |
| **Z4** | 82-93% | Lactate threshold | threshold runs (T), cruise intervals |
| **Z5** | 93-100% | VO2max | intervals (I), repetitions (R), strides |

---

## 2. 高驰（COROS）EvoLab 6 分区心率对照与映射

高驰手表与 App 默认基于**乳酸阈值心率（LTHR）**划分 6 个区间。在调用 COROS MCP 获取心率数据时，直接按以下标准与 Daniels 训练目的对齐：

| 高驰区间 | 高驰区间代码 | 阈值心率范围 (% LTHR) | 对应 Daniels 课表 | 关键生理指标与指导 |
|---|---|---|---|---|
| **Zone 1** | 恢复区间 (Recovery) | 50% - 68% LTHR | **E 跑下限 / 排酸慢跑** | 主动恢复，无心血管负担 |
| **Zone 2** | 有氧耐力 (Aerobic Endurance)| 69% - 84% LTHR | **E 跑 (Easy Aerobic Base)** | **周跑量核心（占 70-80%）**，线粒体与毛细血管奠基 |
| **Zone 3** | 有氧动力 (Aerobic Power) | 85% - 95% LTHR | **M 跑 (Marathon Pace)** | 马拉松专项肌耐力，糖脂混合供能 |
| **Zone 4** | 阈值区间 (Threshold) | 95% - 105% LTHR | **T 跑 (Lactate Threshold)** | 抗乳酸能力提升，持续 20-40 分钟或巡航间歇 |
| **Zone 5** | 无氧动力 (Anaerobic Power) | 106% - 120% LTHR | **I 跑 (VO2max Intervals)** | 最大摄氧量间歇，组间心率需回落 |
| **Zone 6** | 无氧耐力 (Anaerobic Endurance)| > 120% LTHR | **R 跑 (Repetitions)** | 神经肌肉募集效率、跑步经济性（Running Economy）、无氧冲刺 |

---

## 3. 环境与算法干扰校正法则

### ① 高温高湿散热代偿（详见 `weather_adjustment.md`）
- 当环境气温 > 22°C 且相对湿度 > 70%（或露点温度 > 18°C）时，**同等配速下心率漂移或偏高 5-10 bpm 属于正常的皮肤散热代偿**。
- **校正规则**：此时禁止将跑者判定为“心率爆表”或“有氧能力衰退”，应根据环境折算允许其 Z2 跑配速放慢或心率上限上浮 5 bpm。

### ② 手表光电心率计生理滞后说明
- **骤变滞后（Sawtooth Lag）**：间歇冲刺（I/R 跑）时，光电心率存在约 10-20 秒的生理血流与算法平滑延迟，前 100-200 米心率未达到真实峰值属正常生理现象，切勿因初期心率未到而盲目加速冲刺。
