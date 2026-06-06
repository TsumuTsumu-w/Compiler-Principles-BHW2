# 编译原理大作业2 — 类 Rust 词法/语法/语义分析器

在大作业1的基础上实现语义分析、中间代码生成部分。大作业1仓库：https://github.com/gbz666/Compiler-Principles.git

## 直接使用（无需安装任何环境）

双击 `big_hw_2/bighw2/dist/RustAnalyzer.exe`，浏览器会自动打开分析界面。
输入代码，点击"分析"即可查看 Token、AST 和语义诊断结果。
按 `Ctrl+C` 或关闭终端窗口停止服务器。

## 目录结构

```
big_hw_2/
├── bighw2/                # Python 后端
│   ├── lexer.py           # 词法分析器（手写 DFA）
│   ├── parser.py          # 递归下降语法分析器 + 语义检查
|   ├── semantic.py        # 语义分析器
│   ├── analyze_source.py  # JSON 桥接层
│   ├── server.py          # 一体化 HTTP 服务器
│   ├── analyzer.spec      # PyInstaller 打包配置
│   ├── dist/
│   │   └── RustAnalyzer.exe   # 最终可执行文件
│   ├── test_lexer.py      # 词法分析器测试
│   ├── test_parser.py     # 语法/语义分析器测试
|   └── test_semantic.py   # 语义分析器测试
│
└── frontend/              # Vue 3 前端
    ├── src/               # 源码
    └── package.json
```

## 开发 & 重新打包

环境要求：Python 3.10+、Node.js 18+、pnpm

```bash
# 安装前端依赖（仅首次）
cd big_hw_2/frontend
pnpm install

# 安装 PyInstaller（仅首次）
pip install pyinstaller

# 重新构建前端 + 打包为 exe
cd big_hw_2/frontend
pnpm build
cd ../bighw2
pyinstaller analyzer.spec --clean -y
```

打包产物位于 `big_hw_2/bighw2/dist/RustAnalyzer.exe`。

## 运行测试

```bash
cd big_hw_2/bighw2
python test_lexer.py
python test_parser.py
python test_semantic.py
```
