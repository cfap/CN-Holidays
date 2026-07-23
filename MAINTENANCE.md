# 年度更新指南

本订阅源需要在国务院办公厅公布下一年度节假日安排后更新一次。每年
**11 月 15 日起**，如果 `data/` 中还没有下一年度数据，`make check`
会返回年度更新提醒并指向本文档。

订阅日历本身也会在每年公历 **12 月 1 日上午 9 点**显示“日历订阅源需要更新到明年”，用于提醒维护者完成下一年度数据更新。

## 在另一台电脑上开始

确保电脑已安装 Git 和 Python 3，然后执行：

```bash
git clone https://github.com/cfap/CN-Holidays.git
cd CN-Holidays
git pull --ff-only
```

如果已经克隆过仓库，只需进入仓库并运行 `git pull --ff-only`。

## 创建下一年度数据

将年份替换为需要新增的年份：

```bash
make new-year YEAR=2027
```

没有 `make` 时可直接运行 `python3 scripts/scaffold_year.py 2027`。

该命令会创建 `data/2027.json`，并自动计算：

- 情人节：2 月 14 日
- 母亲节：5 月第二个星期日
- 父亲节：6 月第三个星期日

七夕节使用中国农历七月初七，公历日期每年不同。数据骨架会保留
`TODO`，请在[香港天文台公历与农历日期对照表](https://www.hko.gov.hk/tc/gts/time/conversion.htm)
中核对当年的“七月初七”后填写。

## 年度检查清单

1. 根据国务院办公厅通知填写 `document_number`、`source_url`、放假区间、
   补班日期和放假安排摘要。
2. 完成七夕节的公历日期和说明。
3. 确认新年度使用 `revision: 0`；若修改已经发布的年度，则递增其
   `revision` 并更新 `last_modified`。
4. 搜索并清除全部占位内容：

   ```bash
   rg -n "TODO" data
   ```

5. 更新 `README.md` 的年度数据表，以及 `docs/index.html` 中展示的年份和
   官方通知链接。
6. 生成并验证发布文件：

   ```bash
   make generate
   make check
   make test
   ```

7. 检查改动后提交并推送：

   ```bash
   git status
   git add README.md MAINTENANCE.md data docs scripts tests Makefile
   git commit -m "feat: add 2027 calendar data"
   git push
   ```

GitHub Pages 会从 `main` 分支的 `/docs` 目录重新发布。已有订阅者无需更换
订阅地址，客户端会在后续刷新时获取新年度事件。
