import { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Form, Input, Button, Checkbox, message } from 'antd';
import { UserOutlined, LockOutlined } from '@ant-design/icons';
import useAuthStore from '@/stores/useAuthStore';
import { SYSTEM_NAME } from '@/constants';
import { isAuthenticated } from '@/utils/auth';

const REMEMBER_KEY = 'bid_system_remember_username';

export default function LoginPage() {
  const navigate = useNavigate();
  const { login, loading } = useAuthStore();
  const [form] = Form.useForm();

  useEffect(() => {
    if (isAuthenticated()) {
      navigate('/', { replace: true });
      return;
    }
    const saved = localStorage.getItem(REMEMBER_KEY);
    if (saved) {
      form.setFieldsValue({ username: saved, remember: true });
    }
  }, [navigate, form]);

  const handleSubmit = async (values: LoginParams & { remember?: boolean }) => {
    try {
      await login({ username: values.username, password: values.password });
      if (values.remember) {
        localStorage.setItem(REMEMBER_KEY, values.username);
      } else {
        localStorage.removeItem(REMEMBER_KEY);
      }
      message.success('登录成功');
      navigate('/', { replace: true });
    } catch {
      message.error('登录失败，请检查用户名和密码');
    }
  };

  return (
    <div
      style={{
        display: 'flex',
        justifyContent: 'center',
        alignItems: 'center',
        minHeight: '100vh',
        background: '#042f2e',
        position: 'relative',
        overflow: 'hidden',
      }}
    >
      {/* Teal glow orbs */}
      <div
        style={{
          position: 'absolute',
          width: 500,
          height: 500,
          borderRadius: '50%',
          background: 'radial-gradient(circle, rgba(13, 148, 136, 0.3) 0%, transparent 70%)',
          top: '-10%',
          right: '-5%',
          filter: 'blur(60px)',
          pointerEvents: 'none',
        }}
      />
      <div
        style={{
          position: 'absolute',
          width: 400,
          height: 400,
          borderRadius: '50%',
          background: 'radial-gradient(circle, rgba(20, 184, 166, 0.25) 0%, transparent 70%)',
          bottom: '-10%',
          left: '-5%',
          filter: 'blur(60px)',
          pointerEvents: 'none',
        }}
      />

      <div
        style={{
          width: 400,
          padding: '48px 40px 36px',
          background: 'rgba(255, 255, 255, 0.05)',
          backdropFilter: 'blur(20px)',
          WebkitBackdropFilter: 'blur(20px)',
          borderRadius: 20,
          border: '1px solid rgba(255, 255, 255, 0.08)',
          boxShadow: '0 25px 50px rgba(0, 0, 0, 0.3)',
          position: 'relative',
          zIndex: 1,
        }}
      >
        {/* Logo */}
        <div style={{ textAlign: 'center', marginBottom: 36 }}>
          <div
            style={{
              width: 56,
              height: 56,
              borderRadius: 14,
              background: 'linear-gradient(135deg, #0d9488, #14b8a6)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              margin: '0 auto 20px',
              boxShadow: '0 8px 24px rgba(13, 148, 136, 0.35)',
            }}
          >
            <span style={{ fontSize: 22, color: '#fff', fontWeight: 700 }}>B</span>
          </div>
          <h1
            style={{
              fontSize: 22,
              fontWeight: 700,
              background: 'linear-gradient(135deg, #0d9488, #14b8a6)',
              WebkitBackgroundClip: 'text',
              WebkitTextFillColor: 'transparent',
              marginBottom: 6,
            }}
          >
            {SYSTEM_NAME}
          </h1>
          <p style={{ color: 'rgba(255, 255, 255, 0.45)', fontSize: 13, margin: 0 }}>
            请登录您的账户以继续
          </p>
        </div>

        <Form form={form} onFinish={handleSubmit} autoComplete="off">
          <Form.Item name="username" rules={[{ required: true, message: '请输入用户名' }]} style={{ marginBottom: 20 }}>
            <Input
              prefix={<UserOutlined style={{ color: 'rgba(255,255,255,0.3)' }} />}
              placeholder="用户名"
              style={{
                background: 'rgba(255, 255, 255, 0.06)',
                border: '1px solid rgba(255, 255, 255, 0.1)',
                borderRadius: 10,
                height: 46,
                color: '#fff',
                fontSize: 14,
              }}
            />
          </Form.Item>

          <Form.Item name="password" rules={[{ required: true, message: '请输入密码' }]} style={{ marginBottom: 20 }}>
            <Input.Password
              prefix={<LockOutlined style={{ color: 'rgba(255,255,255,0.3)' }} />}
              placeholder="密码"
              style={{
                background: 'rgba(255, 255, 255, 0.06)',
                border: '1px solid rgba(255, 255, 255, 0.1)',
                borderRadius: 10,
                height: 46,
                color: '#fff',
                fontSize: 14,
              }}
            />
          </Form.Item>

          <Form.Item name="remember" valuePropName="checked" style={{ marginBottom: 24 }}>
            <Checkbox style={{ color: 'rgba(255,255,255,0.5)' }}>记住我</Checkbox>
          </Form.Item>

          <Form.Item style={{ marginBottom: 0 }}>
            <Button
              type="primary"
              htmlType="submit"
              loading={loading}
              block
              style={{
                height: 46,
                borderRadius: 10,
                fontSize: 15,
                fontWeight: 600,
                background: 'linear-gradient(135deg, #0d9488, #14b8a6)',
                border: 'none',
                boxShadow: '0 4px 14px rgba(13, 148, 136, 0.35)',
              }}
            >
              登 录
            </Button>
          </Form.Item>
        </Form>
      </div>
    </div>
  );
}
