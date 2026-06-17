import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { useState } from 'react';
import Layout from './components/Layout';
import Dashboard from './pages/Dashboard';
import ProductsManagement from './pages/ProductsManagement';
import RunOperations from './pages/RunOperations';
import RunsList from './pages/RunsList';
import RunDetail from './pages/RunDetail';
import FnlManagement from './pages/FnlManagement';
import Portal from './pages/Portal';
import Login from './pages/Login';
import { getAuthToken } from './services/api';
import { I18nProvider } from './i18n';

function App() {
  const [isAuthenticated, setIsAuthenticated] = useState(() => Boolean(getAuthToken()));

  const handleLogin = () => {
    setIsAuthenticated(true);
  };

  return (
    <I18nProvider>
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
                    <Route path="runs/list" element={<RunsList />} />
                    <Route path="runs/:season/:region/:runId" element={<RunDetail />} />
                    <Route path="runs" element={<RunOperations />} />
                    <Route path="fnl" element={<FnlManagement />} />
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
    </I18nProvider>
  );
}

export default App;
