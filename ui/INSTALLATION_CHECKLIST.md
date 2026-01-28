# Installation & Testing Checklist

## ✅ Pre-Installation Verification

- [x] Python 3.8+ installed
- [x] Node.js 18+ installed
- [x] npm installed
- [x] Bot repository exists at `~/clawd/tmp/repos/polymarket-arbitrage-bot/`
- [x] UI directory created at `~/clawd/tmp/repos/polymarket-arbitrage-bot/ui/`

## 📦 Files Created

### Backend
- [x] `backend/app/__init__.py`
- [x] `backend/app/main.py` (559 lines, FastAPI application)
- [x] `backend/requirements.txt` (6 dependencies)

### Frontend
- [x] `frontend/src/main.jsx` (React entry point)
- [x] `frontend/src/App.jsx` (192 lines, main app)
- [x] `frontend/src/index.css` (Tailwind imports)
- [x] `frontend/src/components/Dashboard.jsx` (106 lines)
- [x] `frontend/src/components/Configuration.jsx` (344 lines)
- [x] `frontend/src/components/Trades.jsx` (161 lines)
- [x] `frontend/src/components/Logs.jsx` (147 lines)
- [x] `frontend/index.html`
- [x] `frontend/package.json`
- [x] `frontend/vite.config.js`
- [x] `frontend/tailwind.config.js`
- [x] `frontend/postcss.config.js`

### Documentation & Scripts
- [x] `start.sh` (executable startup script)
- [x] `README.md` (7.2KB comprehensive guide)
- [x] `QUICKSTART.md` (1.8KB quick start)
- [x] `DEPLOYMENT_SUMMARY.md` (10KB technical summary)
- [x] `INSTALLATION_CHECKLIST.md` (this file)
- [x] `.gitignore` (security & cleanup)

## 🧪 Testing Steps

### 1. File Permissions
```bash
cd ~/clawd/tmp/repos/polymarket-arbitrage-bot/ui
chmod +x start.sh
```
- [x] Startup script is executable

### 2. Backend Installation
```bash
cd backend
pip install -r requirements.txt
```
Expected output:
- Successfully installed fastapi, uvicorn, python-dotenv, pydantic, python-multipart, psutil

### 3. Frontend Installation
```bash
cd frontend
npm install
```
Expected output:
- Dependencies installed in `node_modules/`
- No critical errors

### 4. Start Backend Manually
```bash
cd backend
python app/main.py
```
Expected output:
- Server starts on http://127.0.0.1:8000
- No import errors
- API docs at http://127.0.0.1:8000/docs

Test endpoints:
- [ ] http://127.0.0.1:8000/api/health returns `{"status": "healthy"}`
- [ ] http://127.0.0.1:8000/api/config returns config JSON
- [ ] http://127.0.0.1:8000/api/status returns status JSON

### 5. Start Frontend Manually
```bash
cd frontend
npm run dev
```
Expected output:
- Vite dev server starts on http://127.0.0.1:3000
- No compilation errors
- Browser opens automatically

Visual checks:
- [ ] UI loads without errors
- [ ] Tab navigation works (Dashboard, Configuration, Trades, Logs)
- [ ] Header displays properly
- [ ] Responsive design works

### 6. Test Startup Script
```bash
cd ~/clawd/tmp/repos/polymarket-arbitrage-bot/ui
./start.sh
```
Expected behavior:
- [ ] Installs dependencies (first run only)
- [ ] Starts backend on port 8000
- [ ] Starts frontend on port 3000
- [ ] Opens browser automatically
- [ ] Both processes run in background
- [ ] `Ctrl+C` stops both cleanly

### 7. Test Configuration Page
In browser at http://127.0.0.1:3000:
- [ ] Navigate to "Configuration" tab
- [ ] All form fields render correctly
- [ ] API keys show as masked (*****)
- [ ] Can update values
- [ ] "Save Configuration" button works
- [ ] Success message appears on save

### 8. Test Dashboard
- [ ] Navigate to "Dashboard" tab
- [ ] Status cards display
- [ ] Bot status shows (running/stopped)
- [ ] P&L metrics visible
- [ ] Start/Stop buttons work

### 9. Test Trades Page
- [ ] Navigate to "Trades" tab
- [ ] Table renders (may be empty)
- [ ] Columns display correctly
- [ ] Auto-refresh works (check after 5 seconds)

### 10. Test Logs Page
- [ ] Navigate to "Logs" tab
- [ ] Logs display (if any)
- [ ] Line selector dropdown works
- [ ] Auto-scroll toggle works
- [ ] Refresh button works
- [ ] Clear logs button works (with confirmation)

### 11. Test Bot Control
From Dashboard:
- [ ] Click "Start Bot" (requires valid config.json in bot root)
- [ ] Status updates to "Running"
- [ ] PID and uptime display
- [ ] CPU/memory metrics show
- [ ] Click "Stop Bot"
- [ ] Status updates to "Stopped"
- [ ] Click "Restart"
- [ ] Bot stops and starts successfully

### 12. Test Real-time Updates
With bot running:
- [ ] Dashboard updates every 5 seconds
- [ ] Trades page refreshes automatically
- [ ] Logs update in real-time
- [ ] No console errors

### 13. Security Verification
- [ ] Backend bound to 127.0.0.1 only (not 0.0.0.0)
- [ ] Frontend dev server on 127.0.0.1
- [ ] Cannot access from external network
- [ ] API keys masked in UI
- [ ] Config updates preserve masked values

### 14. Error Handling
- [ ] Invalid config shows error message
- [ ] API connection failure shows error
- [ ] Form validation works
- [ ] Graceful degradation when bot not running

## 🐛 Common Issues & Solutions

### Port Already in Use
```bash
# Check what's using the port
lsof -i :8000
lsof -i :3000

# Kill processes if needed
kill -9 <PID>
```

### Dependencies Won't Install
```bash
# Backend
python -m pip install --upgrade pip
pip install -r requirements.txt

# Frontend
rm -rf node_modules package-lock.json
npm cache clean --force
npm install
```

### Bot Won't Start from UI
1. Ensure `config.json` exists in bot root
2. Check API credentials are valid
3. View logs in Logs tab for errors
4. Verify Python dependencies installed in bot root

### UI Not Loading
1. Clear browser cache
2. Check browser console for errors (F12)
3. Verify backend is running (check http://127.0.0.1:8000/api/health)
4. Check frontend console for compilation errors

### Configuration Not Saving
1. Check file permissions on config.json
2. Verify backend has write access
3. Check backend logs for errors
4. Ensure config.json is valid JSON

## ✅ Final Checklist

Before considering deployment complete:
- [ ] All files created and in correct locations
- [ ] Startup script is executable
- [ ] Both manual starts work (backend & frontend)
- [ ] Startup script works end-to-end
- [ ] All 4 tabs load without errors
- [ ] Configuration saves successfully
- [ ] Bot can be started/stopped from UI
- [ ] Real-time updates work
- [ ] Logs display correctly
- [ ] Security measures verified
- [ ] Documentation is complete

## 📊 Success Metrics

When everything works correctly, you should see:
- ✅ Backend running on http://127.0.0.1:8000
- ✅ Frontend running on http://127.0.0.1:3000
- ✅ API docs at http://127.0.0.1:8000/docs
- ✅ All 4 tabs functional
- ✅ No console errors
- ✅ Auto-refresh working (5s interval)
- ✅ Bot control buttons working

## 🎉 Completion

If all checkboxes are checked, the installation is **complete and successful**!

Next steps:
1. Configure your API credentials
2. Set trading parameters
3. Start the bot
4. Monitor performance

Happy trading! 🚀
