import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { useState } from 'react';
import Layout from './components/Layout';
import Dashboard from './pages/Dashboard';
import WorkflowEditor from './pages/WorkflowEditor';
import TaskScheduler from './pages/TaskScheduler';
import ProductsManagement from './pages/ProductsManagement';
import RunOperations from './pages/RunOperations';
import RunDetail from './pages/RunDetail';
import FnlManagement from './pages/FnlManagement';
import Portal from './pages/Portal';
import Login from './pages/Login';

const AUTH_STORAGE_KEY = 'smanager.admin.authenticated';

function App() {
  const [isAuthenticated, setIsAuthenticated] = useState(() => window.sessionStorage.getItem(AUTH_STORAGE_KEY) === 'true');

  const handleLogin = () => {
    window.sessionStorage.setItem(AUTH_STORAGE_KEY, 'true');
    setIsAuthenticated(true);
  };

  return (
    <Router>
      <Routes>
        <Route path="/" element={<Portal />} />
        <Route path="/login" element={<Login onLogin={handleLogin} />} />

        <Route
          path="/admin/*"
          element={
            isAuthenticated ? (
              <Layout>
                <Routes>
                  <Route path="dashboard" element={<Dashboard />} />
                  <Route path="runs/:runId" element={<RunDetail />} />
                  <Route path="runs" element={<RunOperations />} />
                  <Route path="fnl" element={<FnlManagement />} />
                  <Route path="workflow" element={<WorkflowEditor />} />
                  <Route path="scheduler" element={<TaskScheduler />} />
                  <Route path="products" element={<ProductsManagement />} />
                  <Route path="*" element={<Navigate to="/admin/dashboard" replace />} />
                </Routes>
              </Layout>
            ) : (
              <Navigate to="/login" replace state={{ from: window.location.pathname }} />
            )
          }
        />
      </Routes>
    </Router>
  );
}

export default App;
