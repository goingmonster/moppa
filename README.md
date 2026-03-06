# MOPPA Project

一个使用 Vue3 和 FastAPI 构建的全栈应用程序。

## 项目结构

```
moppa/
├── frontend/  # Vue3 前端应用
├── backend/   # FastAPI 后端应用
└── README.md
```

## 快速开始

### 前端 (Vue3)

```bash
cd frontend
npm install
npm run dev
```

前端将在 http://localhost:5173 启动

### 后端 (FastAPI)

```bash
cd backend
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload
```

后端 API 将在 http://localhost:8000 启动

API 文档可在 http://localhost:8000/docs 查看

## 技术栈

- **前端**: Vue 3, TypeScript, Pinia, Vue Router
- **后端**: FastAPI, SQLAlchemy, Uvicorn
- **数据库**: SQLite (默认)