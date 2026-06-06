# 编译原理大作业 — 类 Rust 词法/语法分析器

## 直接使用（无需安装任何环境）

双击 `big_hw_1/bighw1/dist/RustAnalyzer.exe`，浏览器会自动打开分析界面。  
输入代码，点击"分析"即可查看 Token、AST 和语义诊断结果。  
按 `Ctrl+C` 或关闭终端窗口停止服务器。

## 目录结构

```
big_hw_1/
├── bighw1/                # Python 后端
│   ├── lexer.py           # 词法分析器（手写 DFA）
│   ├── parser.py          # 递归下降语法分析器 + 语义检查
│   ├── analyze_source.py  # JSON 桥接层
│   ├── server.py          # 一体化 HTTP 服务器
│   ├── analyzer.spec      # PyInstaller 打包配置
│   ├── dist/
│   │   └── RustAnalyzer.exe   # 最终可执行文件
│   ├── test_lexer.py      # 词法分析器测试
│   └── test_parser.py     # 语法/语义分析器测试
│
└── frontend/              # Vue 3 前端
    ├── src/               # 源码
    └── package.json
```

## 开发 & 重新打包

环境要求：Python 3.10+、Node.js 18+、pnpm

```bash
# 安装前端依赖（仅首次）
cd big_hw_1/frontend
pnpm install

# 安装 PyInstaller（仅首次）
pip install pyinstaller

# 重新构建前端 + 打包为 exe
cd big_hw_1/frontend
pnpm build
cd ../bighw1
pyinstaller analyzer.spec --clean -y
```

打包产物位于 `big_hw_1/bighw1/dist/RustAnalyzer.exe`。

## 运行测试

```bash
cd big_hw_1/bighw1
python test_lexer.py
python test_parser.py
```
