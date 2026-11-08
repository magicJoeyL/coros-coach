# Pace System & Fitness Estimation (Daniels VDOT & COROS EvoLab)

## Core Idea
Use one recent race result, time trial, or **COROS EvoLab Running Performance (高驰跑力)** to estimate current aerobic fitness (Jack Daniels VDOT system), and derive customized training pace zones.

---

## 1. Fitness Estimation Sources (Priority Order)

1. **COROS MCP 体能评估**: `queryFitnessAssessmentOverview` returns `VO2max` / `Running Level` / `Threshold Pace` and 5K/10K/Half/Full predictions; `queryTrainingLoadAssessment` returns `Short-Term Load` / `Long-Term Load` / `Load Ratio` / `Comment`. **2.3.1 契约更正**：实测 MCP 不返回名为 `running_performance`（跑力 0-100）的字段。若要用「高驰跑力」换算 VDOT，须由跑者提供手表/App 截图中的跑力值，再按第 2 节经验对照表估算，不得声称该值由 MCP 直接拉取。
2. **Recent race result**: Best normal-condition result within 3 months (5k / 10k / half / marathon), mapped to VDOT via Daniels lookup table.
3. **Field calibration test**: 5k all-out time trial, or 30-min best-effort run (last 20-min avg pace ≈ 10k race pace / lactate threshold pace).
4. **COROS / Lab Lactate Threshold (LT) pace**: Use measured LT pace directly as the T-zone baseline (most accurate for threshold work).

---

## 2. COROS 跑力与 Daniels VDOT 对照及典型配速区间

| 高驰跑力 (COROS) | Daniels VDOT | E 配速 (Easy) | M 配速 (Marathon) | T 配速 (Threshold) | I 配速 (Interval) | R 配速 (Repetition) |
|---|---|---|---|---|---|---|
| **40 - 44** | **35 - 39** | 6:40 - 7:25 | 6:00 - 6:35 | 5:35 - 6:05 | 5:05 - 5:30 | 4:45 - 5:05 |
| **45 - 49** | **40 - 44** | 5:55 - 6:35 | 5:15 - 5:50 | 4:55 - 5:25 | 4:28 - 4:55 | 4:05 - 4:28 |
| **50 - 54** | **45 - 49** | 5:25 - 6:00 | 4:48 - 5:15 | 4:28 - 4:50 | 4:00 - 4:25 | 3:40 - 4:00 |
| **55 - 59** | **50 - 54** | 4:58 - 5:30 | 4:25 - 4:45 | 4:05 - 4:25 | 3:40 - 4:00 | 3:22 - 3:40 |
| **60 - 64** | **55 - 59** | 4:35 - 5:05 | 4:05 - 4:25 | 3:48 - 4:05 | 3:25 - 3:42 | 3:08 - 3:22 |
| **65+** | **60+** | ≤ 4:20 | ≤ 3:55 | ≤ 3:35 | ≤ 3:12 | ≤ 2:55 |

> 注：配速单位为 分:秒/千米。具体每 1 点 VDOT 对应详细秒级配速依据 Daniels Running Formula 换算。

---

## 3. Pace Rules & Environmental Calibration

- **E 跑原则（宁慢勿快）**：以有氧心率（Z2 天花板）为首要边界；若气温高或身体疲劳，允许比标定 E 配速放慢 15-30 秒/km，坚决不超心率。
- **M 跑原则（目标导向）**：用于周期化中的专项肌耐力刺激，必须基于可实现的当前 VDOT，严禁直接按远期虚幻目标盲目加速。
- **T 跑原则（乳酸稳态）**：心率应稳定在 LTHR 的 95%-105%（高驰 Zone 4）；持续跑 20-30 分钟，不应出现心率持续失控飙升。
- **I 跑原则（摄氧刺激）**：每组 3-5 分钟（如 800m-1200m 重复），以 VO2max 强度刺激心肺；后半组应达到高驰 Zone 5。
- **R 跑原则（力学经济性）**：短程快速冲刺（200m-400m），注重动作结构、高步频与弹性，间歇必须充分休息至身体恢复。
- **环境温湿度修正**：遇高温高湿（露点 > 18°C），严格执行 `references/weather_adjustment.md`，将 T/M 配速下调 5-15 秒/km，防热衰竭。

---

## 4. Output Template (Route G)

```markdown
## 配速体系与能力标定 — [基于高驰跑力 XX / X 比赛成绩]
当前 VDOT 估算值：≈ [XX] (对应全马潜力约 X:XX:XX)

| 课次类型 | 对应配速区间 | 目标心率区间 | 核心生理目的 |
|---|---|---|---|
| **E (轻松跑/LSD)** | X:XX - X:XX /km | Z1-Z2 (≤84% LTHR) | 毛细血管增生，脂肪代谢 |
| **M (马拉松配速)** | X:XX - X:XX /km | Z3 (85-95% LTHR) | 专项肌耐力，马拉松节奏 |
| **T (乳酸门槛跑)** | X:XX - X:XX /km | Z4 (95-105% LTHR) | 提高乳酸清除门槛 |
| **I (最大摄氧间歇)**| X:XX - X:XX /km | Z5 (106-120% LTHR)| VO2max 心肺峰值刺激 |
| **R (冲刺跑/跨步)** | X:XX - X:XX /km | Z6 (>120% LTHR) | 神经协调，跑步经济性 |

*下次标定建议*：建议在 [日期] 完成一次 5K 计时跑或高驰阈值测试以动态刷新 VDOT。
```
