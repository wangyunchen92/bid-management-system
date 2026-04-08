import { Card, Typography } from 'antd';
import { DashboardOutlined } from '@ant-design/icons';

const { Title, Text } = Typography;

export default function DashboardPage() {
  return (
    <Card>
      <div style={{ textAlign: 'center', padding: '80px 0' }}>
        <DashboardOutlined style={{ fontSize: 48, color: '#0d9488', marginBottom: 16 }} />
        <Title level={3}>招投标管理平台</Title>
        <Text type="secondary">仪表盘开发中，Phase 1 将实现经营大盘数据</Text>
      </div>
    </Card>
  );
}
