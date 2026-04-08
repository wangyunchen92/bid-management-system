import { Suspense, lazy } from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';

import BlankLayout from '@/layouts/BlankLayout';
import BasicLayout from '@/layouts/BasicLayout';

const Login = lazy(() => import('@/pages/Login'));
const Dashboard = lazy(() => import('@/pages/Dashboard'));
const Workflow = lazy(() => import('@/pages/Workflow'));
const Dict = lazy(() => import('@/pages/System/Dict'));
const Department = lazy(() => import('@/pages/System/Department'));
const User = lazy(() => import('@/pages/System/User'));
const Role = lazy(() => import('@/pages/System/Role'));

export default function AppRoutes() {
  return (
    <Suspense fallback={null}>
      <Routes>
        <Route element={<BlankLayout />}>
          <Route path="/login" element={<Login />} />
        </Route>
        <Route element={<BasicLayout />}>
          <Route path="/dashboard" element={<Dashboard />} />
          <Route path="/workflow" element={<Workflow />} />
          <Route path="/system/department" element={<Department />} />
          <Route path="/system/user" element={<User />} />
          <Route path="/system/role" element={<Role />} />
          <Route path="/system/dict" element={<Dict />} />
        </Route>
        <Route path="/" element={<Navigate to="/dashboard" replace />} />
        <Route path="*" element={<Navigate to="/dashboard" replace />} />
      </Routes>
    </Suspense>
  );
}
