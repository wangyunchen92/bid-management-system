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
const Enterprise = lazy(() => import('@/pages/System/Enterprise'));
const TenderList = lazy(() => import('@/pages/Tender/List'));
const TenderForm = lazy(() => import('@/pages/Tender/Form'));
const TenderCalendar = lazy(() => import('@/pages/Tender/Calendar'));
const Decision = lazy(() => import('@/pages/Decision'));
const Opening = lazy(() => import('@/pages/Opening'));
const Qualification = lazy(() => import('@/pages/Library/Qualification'));
const Achievement = lazy(() => import('@/pages/Library/Achievement'));
const PersonnelCert = lazy(() => import('@/pages/Library/PersonnelCert'));
const ProductPage = lazy(() => import('@/pages/Library/Product'));
const BidList = lazy(() => import('@/pages/Bid/List'));
const BidWorkbench = lazy(() => import('@/pages/Bid/Workbench'));
const KnowledgeList = lazy(() => import('@/pages/Knowledge'));

export default function AppRoutes() {
  return (
    <Suspense fallback={null}>
      <Routes>
        <Route element={<BlankLayout />}>
          <Route path="/login" element={<Login />} />
        </Route>
        <Route element={<BasicLayout />}>
          <Route path="/dashboard" element={<Dashboard />} />
          <Route path="/tender/list" element={<TenderList />} />
          <Route path="/tender/create" element={<TenderForm />} />
          <Route path="/tender/calendar" element={<TenderCalendar />} />
          <Route path="/tender/:id" element={<TenderForm />} />
          <Route path="/decision/list" element={<Decision />} />
          <Route path="/opening/list" element={<Opening />} />
          <Route path="/library/qualification" element={<Qualification />} />
          <Route path="/library/achievement" element={<Achievement />} />
          <Route path="/library/personnel-cert" element={<PersonnelCert />} />
          <Route path="/library/product" element={<ProductPage />} />
          <Route path="/bid/list" element={<BidList />} />
          <Route path="/bid/:id" element={<BidWorkbench />} />
          <Route path="/knowledge/list" element={<KnowledgeList />} />
          <Route path="/workflow" element={<Workflow />} />
          <Route path="/system/department" element={<Department />} />
          <Route path="/system/user" element={<User />} />
          <Route path="/system/role" element={<Role />} />
          <Route path="/system/dict" element={<Dict />} />
          <Route path="/system/enterprise" element={<Enterprise />} />
        </Route>
        <Route path="/" element={<Navigate to="/dashboard" replace />} />
        <Route path="*" element={<Navigate to="/dashboard" replace />} />
      </Routes>
    </Suspense>
  );
}
