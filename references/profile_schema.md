# Profile Schema (field reference & example)

This skill reads physiological parameters, environment preferences, race calendar goals, and readiness gate settings from `~/.workbuddy/coros-running-coach/profile.json`. On first use (or if missing) it guides the user to create it. The values below are **generic placeholders, not real data** — only to show the format.

> **Sensitive data note:** Physiological and health-related fields (heart rate, lactate threshold, injury history) are sensitive personal data. Providing them is **optional** — they only personalize pacing and risk screening, the skill works without them. All data stays in the local file on your machine; the skill never transmits it anywhere. Skip any question you prefer not to answer.

```json
{
  "location": {
    "city": "北京",
    "district": "朝阳区",
    "country": "中国"
  },
  "coros": {
    "device_model": "COROS PACE 3",
    "sync_enabled": true,
    "user_id": ""
  },
  "weather_preference": {
    "heat_sensitive": true,
    "sweat_rate": "high",
    "dew_point_alert_c": 18
  },
  "readiness_gate": {
    "enabled": true,
    "min_sleep_score": 60,
    "min_deep_sleep_min": 35,
    "max_rest_hr_elevation": 5
  },
  "weight_kg": 65,
  "rest_hr": 50,
  "max_hr": 190,
  "lactate_threshold": { "hr": 175, "pace": "4:15", "power": 320 },
  "zones": {
    "method": "LT%",
    "z1": { "hr": [95, 119] },
    "z2": { "hr": [120, 147] },
    "z3": { "hr": [148, 166] },
    "z4": { "hr": [167, 183] },
    "z5": { "hr": [184, 190] }
  },
  "pbs": {
    "5k": "21:30",
    "10k": "44:50",
    "half_marathon": "1:39:20",
    "full_marathon": "3:29:15"
  },
  "goal": {
    "target_race": {
      "name": "北京马拉松",
      "alias": "北马",
      "race_date": "2026-11-01",
      "distance": "full_marathon",
      "target_time": "3:15:00",
      "target_pace": "4:37",
      "course_profile": "flat_city"
    },
    "macrocycle": {
      "total_weeks": 16,
      "current_week": 8,
      "current_phase": "build"
    }
  },
  "history": {
    "injuries": [],
    "training_years": 3,
    "weekly_mileage_base": 55
  },
  "current_phase": {
    "name": "build",
    "weekly_mileage": "60-70",
    "quality_sessions_per_week": 2
  }
}
```

## Field notes
- **location.city**: 常驻城市（如北京、上海、无锡、广州、成都）。用于自动联动气象工具查询训练实况温湿度或排定未来一周课表时的天气趋势。
- **goal.target_race**:
  - `alias`: 支持国内主流马拉松简称（如“北马”、“上马”、“锡马”、“厦马”、“汉马”、“重马”等）；
  - `race_date`: 比赛日（YYYY-MM-DD）。系统自动根据当前日期推算倒计时周数（Weeks to Race）；
  - `macrocycle`: 自动映射 16-18 周 Daniels/Pfitzinger 经典大周期（Base 基础期 → Build 提高期 → Peak 巅峰期 → Taper 减量期）。
- **readiness_gate**:
  - `min_sleep_score`: 开跑前晨间门禁最低睡眠分（默认 60 分）；
  - `min_deep_sleep_min`: 开跑前最低深睡分钟数（默认 35 分钟）；
  - `max_rest_hr_elevation`: 晨脉较近期基线上浮报警阈值（默认 +5 bpm）。
- **coros.sync_enabled**: 是否启用高驰 MCP 主动同步。启用后一键拉取运动、睡眠、负荷与恢复数据。
- **zones.method**: `HRR` / `LT%` / `MaxHR%`。高驰 EvoLab 默认建议使用 `LT%`。
- **history.injuries**: 过往伤病历史，用于伤病筛查及力量恢复针对性规避。

## Setup questions (when profile.json missing)

All questions are optional — answer only what you are comfortable sharing:

1. 常驻城市（用于天气温湿度感知）及高驰手表型号
2. 目标赛事（如“今年北马”或“明年锡马”）与目标完赛时间（A/B/C 目标）
3. 年龄、静息心率（晨脉）、实测/估算最大心率、乳酸阈值心率及配速
4. 近期个人最好成绩 PBs (5k / 10k / 半马 / 全马)
5. 跑龄、近期稳定周跑量基数、过往伤病历史
6. 当前所处的训练阶段（基础期/提高期/巅峰期/减量期）
