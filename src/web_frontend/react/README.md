# React Frontend

This folder is reserved for a React-based frontend when migrating to full SPA.

Future structure:
```
react/
├── package.json
├── src/
│   ├── App.tsx
│   ├── components/
│   ├── services/
│   └── styles/
├── public/
└── build/
```

This would be a separate Node.js project that builds to static files served by nginx.

Currently, all frontend implementations are in `../web_frontend.py`.
