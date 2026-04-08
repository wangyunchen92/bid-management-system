import { Outlet } from 'react-router-dom';

export default function BlankLayout() {
  return (
    <div style={{ minHeight: '100vh' }}>
      <Outlet />
    </div>
  );
}
