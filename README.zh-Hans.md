<div align="center">
  <h1>Luogu Solution</h1>
  <p><a href="README.md">English</a> · <strong>简体中文</strong></p>
  <p>
    <img src="https://img.shields.io/github/actions/workflow/status/lailai0916/luogu-solution/ci.yml?branch=main&style=flat-square" />
    <img src="https://img.shields.io/github/last-commit/lailai0916/luogu-solution?style=flat-square" />
    <img src="https://img.shields.io/github/languages/top/lailai0916/luogu-solution?style=flat-square" />
    <img src="https://img.shields.io/github/repo-size/lailai0916/luogu-solution?style=flat-square" />
    <img src="https://img.shields.io/github/license/lailai0916/luogu-solution?style=flat-square" />
  </p>
</div>

## 项目简介

这是覆盖完整洛谷题解流程的 runtime-neutral Agent Skill。它负责抓取官方题面、参考已有
题解、独立推导与验证、对拍、撰写细致题解，并安全地新建或同步洛谷专栏。

## 项目特性

- **官方源优先** —— 题面、限制、样例与当前投稿规范均以洛谷为权威源。
- **候选资格硬闸门** —— 只处理难度至少为紫、题解通道开放、现有题解不超过 3 篇，且
  当前账号从未写过题解的题目；运行时配置不得放宽阈值。
- **先正确，再成文** —— 证明、编译、样例、边界测试与确定性对拍统一执行。
- **流程保证原创** —— 独立代码与完整初稿形成检查点后才能读取已有题解，之后必须按
  推导、符号、论证、变量与控制流五个维度检查相似性，并把审计绑定到当前产物与完整
  引用台账。
- **官方测评审核闸门** —— 投稿审核前，当前账号必须存在同题号、且与缓存源码完全一致的
  Accepted 记录，题解参考代码也必须与其一致；本地验证或另一份 AC 代码均不能替代。
- **细致 OI 题解** —— 正文最高只用 H2，完整说明本题特有的推导、正确性、实现对应与
  必要复杂度，不用初学者教程式内容凑篇幅。
- **可组合 GNU C++17 风格** —— 内置紧凑默认模板。调用方或目标仓库已有 OI 风格时
  整体替换，并在源头校验；这里不复制规则手册。
- **安全账号操作** —— 密钥只在本机保存；真实写入须当次授权；发布后完整回读；投稿审核
  前必须通过精确源码官方测评闸门；撤回时保留原文章和 `lid`，绝不删除；专用维护接口
  严格区分个人隐藏草稿与公开独立草稿，二者均不能新建文章或请求审核。

## 快速开始

```bash
git clone https://github.com/lailai0916/luogu-solution ~/.agents/skills/luogu-solution
cd ~/.agents/skills/luogu-solution
python3 -m pip install -r requirements.txt
python3 scripts/candidate.py P1001
python3 scripts/fetch.py P1001
```

可将洛谷 Cookie 保存到 `~/.config/luogu-solution/cookie.txt` 并设置权限为 `0600`，也可使用
`LUOGU_COOKIE`。全部题目产物保存在 `~/.cache/luogu/<PID>/`，不会进入本仓库。

## 项目结构

```bash
luogu-solution/
├── agents/                     # Skill 界面元数据
├── assets/                     # 可复用 OI 代码模板
├── references/                 # 工作流、写作、代码与发布规范
├── scripts/                    # 抓取、验证、对拍与发布工具
├── tests/                      # 离线确定性单元测试
└── SKILL.md                    # Runtime-neutral Skill 入口
```

## 许可协议

本项目代码采用 [MIT 许可协议](https://github.com/lailai0916/tools/blob/main/LICENSE)。
