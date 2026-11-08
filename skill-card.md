## Description:

面向耐力跑者的专属 AI 跑步教练（2.3 增强版）：深度绑定高驰（COROS）MCP 接口全维度数据（运动记录、前夜睡眠结构、全天非跑活动与恢复电量），支持“MCP 自动优先 + 跑者截图深度多模态分析”双引擎架构。具备 `--weather` 逐小时气象与露点折算，融合晨间开跑门禁诊断、比赛日配速补给仿真、目标赛事倒计时（需档案日期），以及快捷追问口令文本。

This skill is ready for commercial/non-commercial use.

## Publisher:

[magic-Joey](https://clawhub.ai/user/magic-Joey)

### License/Terms of Use:

MIT-0

### Release Date:

2026-11-08

## Use Case:

耐力跑者（5K、10K、半马至全马）使用本技能通过 COROS MCP 主动拉取手表数据或发送运动截图，结合前夜睡眠、全天日常负荷与环境温湿度露点折算，进行单次深度复盘、晨间开跑门禁诊断、间歇跑诊断、周末长距离评估、比赛日仿真、EvoLab 负荷监控与科学周期化周课表排定。

### Deployment Geography for Use:

Global / China (Workbuddy 深度适配)

## ⚡ Workbuddy 极简快捷指令（开箱即用 4 大口令）：

用户在手机端聊天框可直接一键发送以下预设口令（亦可附带手表截图发送）：
1. **【复盘最近一次跑步】**：自动调用 COROS MCP 拉取运动详情 + 关联前夜睡眠与身体底色 + 联动实况天气 + 六维科学复盘 + 跑后恢复建议 + 追问药丸
2. **【周三间歇诊断】**：提取当周间歇冲刺圈与休息圈数据，诊断各组完成度、心率恢复速率（HR Recovery）与无氧负荷刺激
3. **【周末长距离评估】**：拉取周末长跑分段与高驰训练负荷（TL），评估有氧耐力基底、燃脂效率、后程心率漂移与步态衰减
4. **【结合状态排下周课表】**：调取 VO2max / Running Level / Threshold Pace、Short-Term/Long-Term Load 与 Load Ratio、`--countdown` 倒计时与 `--weather` 天气，定制科学周期化课表

## 核心能力升级亮点：

- **开门第一优先引导高驰 MCP 接入**：安装后首次对话或检测到未连接时，第一位主动引导跑者接入高驰官方 MCP 服务（远程 HTTP + 浏览器 OAuth 授权，无需 npm 包与明文密码），并提供免配置截图兜底通道；
- **双引擎数据输入机制**：首选 COROS MCP 主动拉取，零门槛免截图；同时完全兼容跑者上传的跑步/睡眠截图，通过 OCR 视觉提取深度交叉融合或独立支撑复盘；
- **晨间开跑红绿灯门禁（Pre-Run Readiness Gate）**：结合前夜睡眠评分（<60）、深睡时长（<35m）与晨脉上浮（>+5 bpm），主动给出课表降阶指令，防伤于未然；
- **比赛日配速与补给仿真器（Race Strategy Simulator）**：一键生成 42.195km 全马 5km 分段巡航配速仿真卡与精准到每公里/水站的能量胶、高钠盐丸进补时间表；
- **目标赛事倒计时（需档案日期）**：在 `profile.json` 填 `goal.target_race.race_date`，用 `--countdown` 计算剩余周数与建议阶段。**本技能不内置赛历**，简称无法自动推出日期；阶段划分为经验规则，非 Daniels/Pfitzinger 原法；
- **快捷追问口令（文本）**：每次分析和排课末尾生成 3 条快捷口令文本；是否可点击取决于客户端，不承诺「点击即发送」。
- **当地天气取数已实现**：用 `--weather <纬度> <经度> <日期>` 拉取气温、相对湿度、露点温度与风（open-meteo 逐小时，**非现场实测**，须标注来源）；据此做散热代偿判定与高温排课下调，不得编造天气数值。
- **真人教练主观体感（RPE）追问机制**：当数据发现心率偏高或后程掉速时，主动关怀询问睡眠熬夜、低碳饮食、补水补糖与肌肉酸痛状况，拒绝机械冰冷判读；
- **全套科学运动体系完整保留**：全面继承 Daniels VDOT 配速区间、Pfitzinger 周期化、非诊断性伤病筛查（`injury_check.md`）、即刻停跑红旗指标与营养恢复指南。

## Known Risks and Mitigations:

- **Risk**: A running profile may contain sensitive heart-rate, goal, and injury-history information.
  - **Mitigation**: All profile data stays in the user's local `~/.workbuddy/coros-running-coach/profile.json`; sensitive items are optional.
- **Risk**: Injury and recovery guidance could be mistaken for a medical assessment.
  - **Mitigation**: Strictly non-diagnostic risk screening with immediate medical referral indicators for red flags (chest pain, fainting, sharp/rest pain).

## Reference(s):

- [COROS MCP Mapping](references/coros_mcp_mapping.md)
- [Weather & Dew Point Adjustment](references/weather_adjustment.md)
- [Race Strategy & Fueling Simulator](references/race_tactics.md)
- [Profile Schema & Target Race Date](references/profile_schema.md)
- [Report Templates with Action Pills](references/report_template.md)
- [Weekly review & Week settlement](references/weekly_review.md)
- [Injury screening decision tree](references/injury_check.md)
- [COROS EvoLab & Zone Calculation](references/zone_calc.md)
- [COROS Lap & Metric Headers](references/coros_lap_headers.md)

## Skill Output:

**Output Type(s):** [Markdown, Guidance, Structured Reports, Action Pills]

**Output Format:** [Structured Markdown reports, lap split tables, sleep & readiness cards, pacing cards, interactive action pills]

## Skill Version(s):

2.3.1 (只读白名单 · 天气/档案/赛历倒计时实现 · 字段契约对齐实测 API · 取数修复)
