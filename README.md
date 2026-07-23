# 中国大陆法定节假日与调休订阅日历

这是一个可供 iPhone、iPad、Mac 及其他 iCalendar 客户端订阅的只读日历源。当前只包含 **2026 年**国务院办公厅公布的放假与调休安排；后续年份可按相同格式增补。

- 可发布文件：[`docs/cn-holidays.ics`](docs/cn-holidays.ics)
- 订阅落地页：[`docs/index.html`](docs/index.html)
- 官方依据：[国务院办公厅关于2026年部分节假日安排的通知（国办发明电〔2025〕7号）](https://www.gov.cn/zhengce/zhengceku/202511/content_7047091.htm)

## 2026 年数据

| 节日 | 放假日期（含首尾） | 调休上班日 |
| --- | --- | --- |
| 元旦 | 1 月 1 日—1 月 3 日 | 1 月 4 日 |
| 春节 | 2 月 15 日—2 月 23 日 | 2 月 14 日、2 月 28 日 |
| 清明节 | 4 月 4 日—4 月 6 日 | 无 |
| 劳动节 | 5 月 1 日—5 月 5 日 | 5 月 9 日 |
| 端午节 | 6 月 19 日—6 月 21 日 | 无 |
| 中秋节 | 9 月 25 日—9 月 27 日 | 无 |
| 国庆节 | 10 月 1 日—10 月 7 日 | 9 月 20 日、10 月 10 日 |

日程均为全天日程，使用 `TRANSP:TRANSPARENT`，不会把个人空闲状态标记为忙碌。连续假期按天拆分：除最后一天显示为“节日（最后一天）”外，其余日期显示为“节日（第 n 天）”；调休上班日显示为“节日（补班）”。每个事件的 `DTEND` 均按 RFC 5545 使用“不包含结束日”的写法。

## 发布到 GitHub Pages

先在 GitHub 新建一个空的公开仓库，例如 `CNCalendar`。然后在本目录执行（把 `<你的用户名>` 替换为实际 GitHub 用户名）：

```bash
git init
git add .
git commit -m "Add 2026 China holiday calendar"
git branch -M main
git remote add origin https://github.com/<你的用户名>/CNCalendar.git
git push -u origin main
```

在 GitHub 仓库中打开 **Settings → Pages**：

1. `Source` 选择 **Deploy from a branch**。
2. 分支选择 **main**，目录选择 **/docs**。
3. 点击 **Save**，等待 Pages 发布完成。

发布后地址为：

- 落地页：`https://<你的用户名>.github.io/CNCalendar/`
- HTTPS 订阅源：`https://<你的用户名>.github.io/CNCalendar/cn-holidays.ics`

如果仓库名不是 `CNCalendar`，请同步替换 URL 中的仓库名。GitHub Pages 的发布步骤可参考 [GitHub 官方文档](https://docs.github.com/en/pages/getting-started-with-github-pages/configuring-a-publishing-source-for-your-github-pages-site)。

## 在 iPhone 上订阅

使用 iPhone 打开上面的落地页并轻点“订阅到系统日历”；也可以手动添加：

1. 打开“日历” App，轻点底部的“日历”。
2. 轻点“添加日历” → “添加订阅日历”。
3. 粘贴上面的 **HTTPS 订阅源**并轻点“查找”（旧版 iOS 显示为“订阅”）。
4. 可将账户选为 iCloud，让订阅同步到同一 Apple 账户的其他设备，然后完成添加。

Apple 的最新操作说明见[在 iCloud 中添加日历订阅](https://support.apple.com/zh-cn/102301)。不要只下载并导入 `.ics`；“订阅”才能在 GitHub 上更新文件后由系统定期拉取新内容。

## 后续增补或修改

年度源数据位于 [`data/2026.json`](data/2026.json)。新增年份时复制一份为 `data/2027.json`，更新年度、官方文件、日期及 `last_modified`；如果修订已经发布过的年度数据，请同时递增 `revision`。

生成并检查日历：

```bash
python3 scripts/generate_calendar.py
python3 scripts/generate_calendar.py --check
python3 -m unittest discover -s tests -v
```

也可以运行 `make generate`、`make check` 和 `make test`。提交并推送更新后，GitHub Pages 会重新发布，订阅者无需更换 URL。Apple 客户端的刷新时间由系统控制，不保证推送后立即显示。

## 文件结构

```text
data/2026.json                 # 可维护的官方年度数据
scripts/generate_calendar.py   # 零第三方依赖的 ICS 生成与校验脚本
tests/test_calendar.py         # 日期、事件数及 RFC 5545 基础检查
docs/cn-holidays.ics           # 可直接使用及托管的日历源
docs/index.html                # GitHub Pages 订阅落地页
```
