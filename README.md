# 中国大陆法定节假日、补班与纪念日订阅日历

这是一个可供 iPhone、iPad、Mac 及其他 iCalendar 客户端订阅的只读日历源。当前包含 **2026 年**国务院办公厅公布的放假与补班安排，以及情人节、母亲节、父亲节和七夕节；后续年份可按相同格式增补。

> [!IMPORTANT]
> 本项目需要每年更新。每年 11 月 15 日起，`make check` 会在缺少下一年度数据时给出提示。换电脑维护时请按 [`MAINTENANCE.md`](MAINTENANCE.md) 操作。

- 可发布文件：[`docs/cn-holidays.ics`](docs/cn-holidays.ics)
- 订阅落地页：[`docs/index.html`](docs/index.html)
- 官方依据：[国务院办公厅关于2026年部分节假日安排的通知（国办发明电〔2025〕7号）](https://www.gov.cn/zhengce/zhengceku/202511/content_7047091.htm)
- 农历依据：[香港天文台 2026 年公历与农历日期对照表](https://www.hko.gov.hk/tc/gts/time/calendar/pdf/files/2026.pdf)

## 2026 年数据

| 节日 | 放假日期（含首尾） | 补班日期 |
| --- | --- | --- |
| 元旦 | 1 月 1 日—1 月 3 日 | 1 月 4 日 |
| 春节 | 2 月 15 日—2 月 23 日 | 2 月 14 日、2 月 28 日 |
| 清明节 | 4 月 4 日—4 月 6 日 | 无 |
| 劳动节 | 5 月 1 日—5 月 5 日 | 5 月 9 日 |
| 端午节 | 6 月 19 日—6 月 21 日 | 无 |
| 中秋节 | 9 月 25 日—9 月 27 日 | 无 |
| 国庆节 | 10 月 1 日—10 月 7 日 | 9 月 20 日、10 月 10 日 |

### 纪念日

| 名称 | 2026 年日期 | 日期规则 |
| --- | --- | --- |
| 情人节 | 2 月 14 日 | 每年 2 月 14 日 |
| 母亲节 | 5 月 10 日 | 5 月第二个星期日 |
| 父亲节 | 6 月 21 日 | 6 月第三个星期日 |
| 七夕节 | 8 月 19 日 | 农历七月初七 |

### 事件构成与显示规则

每个年度根据当年的源数据生成以下全天事件：

| 事件类型 | 生成方式 |
| --- | --- |
| 放假日 | 按当年公布的放假区间逐日生成 |
| 补班日期 | 按当年公布的补班日期生成 |
| 纪念日 | 根据年度 JSON 中的纪念日生成 |
| 年度维护 | 每年公历 12 月 1 日自动生成 |

所有事件均使用 `TRANSP:TRANSPARENT`，不会把个人空闲状态标记为忙碌。放假事件的 `DESCRIPTION` 会显示该段假期的总天数，该值由当年放假区间动态计算。纪念日仅作日期标注，不代表法定放假。每个事件的 `DTEND` 均按 RFC 5545 使用“不包含结束日”的写法。

### 事件标题规则

| 类型 | 标题规则 |
| --- | --- |
| 单日假期 | `{节日名}` |
| 多日假期第一天 | `{节日名}假期（第1天）` |
| 多日假期中间日 | `{节日名}假期（第{n}天）` |
| 多日假期最后一天 | `{节日名}假期（最后一天）` |
| 补班日期 | `{节日名}（补班）` |
| 纪念日 | `{纪念日名}` |
| 年度维护 | `日历订阅源需要更新到明年` |

### 提醒规则

| 类型 | 提醒时间 | 提醒文案 |
| --- | --- | --- |
| 单日假期 | 前一天 14:00 | `明天是{节日名}` |
| 单日假期 | 当天 09:00 | `今天是{节日名}` |
| 多日假期第一天 | 前一天 14:00 | `明天开始{节日名}放假` |
| 多日假期第一天 | 当天 09:00 | `{节日名}假期第1天` |
| 多日假期中间日 | 当天 09:00 | `{节日名}假期第{n}天` |
| 多日假期最后一天 | 前一天 14:00 | `明天是{节日名}假期最后一天` |
| 多日假期最后一天 | 当天 09:00 | `{节日名}假期最后一天` |
| 补班日期 | 前一天 14:00 | `明天是{节日名}补班` |
| 补班日期 | 当天 09:00 | `{节日名}补班` |
| 纪念日 | 当天 09:00 | `今天是{纪念日名}` |
| 年度维护 | 12 月 1 日 09:00 | `日历订阅源需要更新到明年` |

当天上午 9 点使用相对事件开始时间的 `TRIGGER:PT9H`；前一天下午 2 点使用 `TRIGGER:-PT10H`。提醒能否显示取决于客户端的日历通知设置。

## 发布到 GitHub Pages

当前仓库为 [`cfap/CN-Holidays`](https://github.com/cfap/CN-Holidays)，发布内容位于 `docs/`。首次启用 GitHub Pages 时，在仓库中打开 **Settings → Pages**：

1. `Source` 选择 **Deploy from a branch**。
2. 分支选择 **main**，目录选择 **/docs**。
3. 点击 **Save**，等待 Pages 发布完成。

按当前账号和仓库名，启用后的发布地址为：

- 落地页：`https://cfap.github.io/CN-Holidays/`
- HTTPS 订阅源：`https://cfap.github.io/CN-Holidays/cn-holidays.ics`

后续提交并推送 `main` 分支后，Pages 会重新发布 `docs/` 中的落地页和订阅文件。如果将项目 Fork 到其他账号或修改仓库名，需要同步替换上述 URL 中的账号或仓库路径。GitHub Pages 的发布步骤可参考 [GitHub 官方文档](https://docs.github.com/en/pages/getting-started-with-github-pages/configuring-a-publishing-source-for-your-github-pages-site)。

## 在 iPhone 上订阅

使用 iPhone 打开上面的落地页并轻点“订阅到系统日历”；也可以手动添加：

1. 打开“日历” App，轻点底部的“日历”。
2. 轻点“添加日历” → “添加订阅日历”。
3. 粘贴上面的 **HTTPS 订阅源**并轻点“查找”（旧版 iOS 显示为“订阅”）。
4. 可将账户选为 iCloud，让订阅同步到同一 Apple 账户的其他设备，然后完成添加。

Apple 的最新操作说明见[在 iCloud 中添加日历订阅](https://support.apple.com/zh-cn/102301)。不要只下载并导入 `.ics`；“订阅”才能在 GitHub 上更新文件后由系统定期拉取新内容。

## 后续增补或修改

完整步骤见 [`MAINTENANCE.md`](MAINTENANCE.md)。创建下一年度数据骨架：

```bash
make new-year YEAR=2027
```

该命令会自动计算情人节、母亲节和父亲节日期；七夕节必须根据农历对照表人工核对。12 月 1 日的年度维护事件由生成器自动创建，无需写入年度 JSON。放假事件的总天数由生成器根据 `start` 和 `end` 自动计算，无需手工维护。年度源数据位于 [`data/`](data/)；如果修订已经发布过的年度数据，请同时递增 `revision` 并更新 `last_modified`。

生成并检查日历：

```bash
python3 scripts/generate_calendar.py
python3 scripts/generate_calendar.py --check
python3 -m unittest discover -s tests -v
```

也可以运行 `make generate`、`make check` 和 `make test`：

- `make generate`：读取全部年度 JSON，生成并校验 `docs/cn-holidays.ics`。
- `make check`：校验年度数据和 RFC 5545 格式，确认已发布的 `.ics` 与当前代码及数据完全一致；每年 11 月 15 日起还会检查下一年度数据是否存在。
- `make test`：检查日期、事件数量、提醒时间与文案、CRLF 换行和 75 字节折行限制。

提交并推送更新后，GitHub Pages 会重新发布，订阅者无需更换 URL。Apple 客户端的刷新时间由系统控制，不保证推送后立即显示。

## 文件结构

```text
data/2026.json                 # 可维护的官方年度数据
MAINTENANCE.md                 # 跨设备年度更新步骤与检查清单
scripts/generate_calendar.py   # 零第三方依赖的 ICS 生成与校验脚本
scripts/scaffold_year.py       # 创建下一年度数据骨架
tests/test_calendar.py         # 日期、事件数、提醒规则及 RFC 5545 检查
docs/cn-holidays.ics           # 可直接使用及托管的日历源
docs/index.html                # GitHub Pages 订阅落地页
```
