import { Suspense, lazy } from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';

import BlankLayout from '@/layouts/BlankLayout';
import BasicLayout from '@/layouts/BasicLayout';

const Login = lazy(() => import('@/pages/Login'));
const Dashboard = lazy(() => import('@/pages/Dashboard'));

export default function AppRoutes() {
  return (
    <Suspense fallback={null}>
      <Routes>
        <Route element={<BlankLayout />}>
          <Route path="/login" element={<Login />} />
        </Route>
        <Route element={<BasicLayout />}>
          <Route path="/dashboard" element={<Dashboard />} />
        </Route>
        <Route path="/" element={<Navigate to="/dashboard" replace />} />
        <Route path="*" element={<Navigate to="/dashboard" replace />} />
      </Routes>
    </Suspense>
  );
}
