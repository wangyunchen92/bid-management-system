import { useEffect } from 'react';
import { ConfigProvider, App as AntdApp } from 'antd';
import zhCN from 'antd/locale/zh_CN';
import { BrowserRouter } from 'react-router-dom';
import dayjs from 'dayjs';
import 'dayjs/locale/zh-cn';

import useAuthStore from '@/stores/useAuthStore';
import AppRoutes from './routes';

dayjs.locale('zh-cn');

const themeConfig = {
  token: {
    colorPrimary: '#0d9488',
    colorSuccess: '#10B981',
    colorWarning: '#D97706',
    colorError: '#EF4444',
    colorInfo: '#0d9488',
    colorBgContainer: '#ffffff',
    colorBgLayout: '#f1f5f9',
    colorBorder: '#e2e8f0',
    colorBorderSecondary: '#e2e8f0',
    colorText: '#0f172a',
    colorTextSecondary: '#475569',
    colorTextTertiary: '#94a3b8',
    borderRadius: 8,
    fontFamily: "'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif",
    fontSize: 14,
    controlHeight: 36,
    boxShadow: '0 1px 3px rgba(0,0,0,0.06), 0 1px 2px rgba(0,0,0,0.04)',
  },
  components: {
    Button: { borderRadius: 8, controlHeight: 36, fontWeight: 500 },
    Card: { borderRadiusLG: 14 },
    Input: { borderRadius: 8, controlHeight: 36 },
    Select: { borderRadius: 8, controlHeight: 36 },
    Table: { borderRadius: 14, headerBg: 'transparent', headerColor: '#94a3b8' },
    Menu: { darkItemBg: 'transparent', darkSubMenuItemBg: 'rgba(0,0,0,0.15)' },
  },
};

export default function App() {
  const { isLoggedIn, fetchCurrentUser } = useAuthStore();

  useEffect(() => {
    if (isLoggedIn) {
      fetchCurrentUser();
    }
  }, [isLoggedIn, fetchCurrentUser]);

  return (
    <ConfigProvider locale={zhCN} theme={themeConfig}>
      <AntdApp>
        <BrowserRouter>
          <AppRoutes />
        </BrowserRouter>
      </AntdApp>
    </ConfigProvider>
  );
}
