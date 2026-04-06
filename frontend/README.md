# 前端 - React + TypeScript + Vite

本前端使用 Vite 搭建，集成 React + TypeScript，支持 HMR 热更新和 ESLint 代码检查。

## 技术栈

- React 19
- TypeScript 5.9
- Vite 8
- WebSocket + SSE 实时通信

## 本地开发

```bash
# 安装依赖
npm install

# 启动开发服务器
npm run dev
# 浏览器打开 http://localhost:5173

# 构建生产版本
npm run build

# 代码检查
npm run lint
```

## 构建插件

当前使用 [@vitejs/plugin-react](https://github.com/vitejs/vite-plugin-react/blob/main/packages/plugin-react)，基于 [Oxc](https://oxc.rs) 编译。

也可以切换为 [@vitejs/plugin-react-swc](https://github.com/vitejs/vite-plugin-react/blob/main/packages/plugin-react-swc)，使用 [SWC](https://swc.rs/) 编译。

## React Compiler

模板默认未启用 React Compiler（影响开发和构建性能）。如需启用，参考[官方文档](https://react.dev/learn/react-compiler/installation)。

## ESLint 配置扩展

生产项目建议启用类型感知的 lint 规则：

```js
export default defineConfig([
  globalIgnores(['dist']),
  {
    files: ['**/*.{ts,tsx}'],
    extends: [
      // 替换 tseslint.configs.recommended 为以下配置
      tseslint.configs.recommendedTypeChecked,
      // 或使用更严格的规则
      tseslint.configs.strictTypeChecked,
      // 可选：风格规则
      tseslint.configs.stylisticTypeChecked,
    ],
    languageOptions: {
      parserOptions: {
        project: ['./tsconfig.node.json', './tsconfig.app.json'],
        tsconfigRootDir: import.meta.dirname,
      },
    },
  },
])
```

也可以安装 [eslint-plugin-react-x](https://github.com/Rel1cx/eslint-react/tree/main/packages/plugins/eslint-plugin-react-x) 和 [eslint-plugin-react-dom](https://github.com/Rel1cx/eslint-react/tree/main/packages/plugins/eslint-plugin-react-dom) 获取 React 专用 lint 规则：

```js
// eslint.config.js
import reactX from 'eslint-plugin-react-x'
import reactDom from 'eslint-plugin-react-dom'

export default defineConfig([
  globalIgnores(['dist']),
  {
    files: ['**/*.{ts,tsx}'],
    extends: [
      reactX.configs['recommended-typescript'],
      reactDom.configs.recommended,
    ],
    languageOptions: {
      parserOptions: {
        project: ['./tsconfig.node.json', './tsconfig.app.json'],
        tsconfigRootDir: import.meta.dirname,
      },
    },
  },
])
```
