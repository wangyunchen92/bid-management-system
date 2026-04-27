import { useEffect, useState } from 'react';
import { Card, Form, Input, Button, Row, Col, Space, App, Spin, Divider } from 'antd';
import { SaveOutlined, ReloadOutlined } from '@ant-design/icons';
import { getEnterpriseProfile, updateEnterpriseProfile, type EnterpriseProfile } from '@/services/system';

export default function EnterprisePage() {
  const { message } = App.useApp();
  const [form] = Form.useForm<EnterpriseProfile>();
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [updatedAt, setUpdatedAt] = useState<string | undefined>();

  const load = async () => {
    setLoading(true);
    try {
      const res = await getEnterpriseProfile();
      form.setFieldsValue(res.data);
      setUpdatedAt(res.data.updated_at);
    } catch (err: any) {
      message.error(`加载失败：${err?.message || err}`);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { void load(); }, []);

  const handleSave = async () => {
    const values = await form.validateFields();
    setSaving(true);
    try {
      await updateEnterpriseProfile(values);
      message.success('保存成功，所有标书的占位符将使用最新企业信息');
      await load();
    } catch (err: any) {
      message.error(`保存失败：${err?.message || err}`);
    } finally {
      setSaving(false);
    }
  };

  const sectionStyle: React.CSSProperties = {
    fontSize: 14,
    fontWeight: 600,
    color: '#0d9488',
    margin: '8px 0',
  };

  return (
    <Card
      title="企业信息配置"
      extra={
        <Space>
          {updatedAt && (
            <span style={{ color: '#94a3b8', fontSize: 12 }}>
              最近更新：{updatedAt.slice(0, 19).replace('T', ' ')}
            </span>
          )}
          <Button icon={<ReloadOutlined />} onClick={load} disabled={loading || saving}>
            刷新
          </Button>
          <Button
            type="primary"
            icon={<SaveOutlined />}
            loading={saving}
            onClick={handleSave}
            style={{ background: 'linear-gradient(135deg, #0d9488, #14b8a6)', border: 'none' }}
          >
            保存
          </Button>
        </Space>
      }
      style={{ margin: 16 }}
    >
      <div style={{ color: '#64748b', fontSize: 13, marginBottom: 16 }}>
        ⚠️ 此处配置会作为标书章节模板的<b>占位符填值数据源</b>
        （响应函/授权书/法定代表人身份证明书/报价表 等都会用这里的值），修改保存后生成的新标书章节会立即采用最新值。
      </div>

      <Spin spinning={loading}>
        <Form form={form} layout="vertical" disabled={saving}>
          <div style={sectionStyle}>基础信息</div>
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item label="公司名称" name="company_name" rules={[{ required: true, message: '必填' }]}>
                <Input placeholder="如：合肥新安彩印包装有限公司" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item label="统一社会信用代码" name="company_credit_code">
                <Input placeholder="18 位信用代码" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item label="公司地址" name="company_address">
                <Input placeholder="如：合肥市长江西路蜀鑫大道12号" />
              </Form.Item>
            </Col>
            <Col span={6}>
              <Form.Item label="公司电话" name="company_phone">
                <Input />
              </Form.Item>
            </Col>
            <Col span={6}>
              <Form.Item label="公司传真" name="company_fax">
                <Input />
              </Form.Item>
            </Col>
            <Col span={6}>
              <Form.Item label="邮政编码" name="company_zipcode">
                <Input />
              </Form.Item>
            </Col>
            <Col span={9}>
              <Form.Item label="开户银行" name="company_bank">
                <Input />
              </Form.Item>
            </Col>
            <Col span={9}>
              <Form.Item label="银行账号" name="company_bank_account">
                <Input />
              </Form.Item>
            </Col>
          </Row>

          <Divider style={{ margin: '8px 0 16px' }} />
          <div style={sectionStyle}>企业详情（用于法定代表人身份证明书）</div>
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item label="单位性质" name="company_type">
                <Input placeholder="如：有限责任公司（自然人投资或控股）" />
              </Form.Item>
            </Col>
            <Col span={6}>
              <Form.Item label="成立时间" name="company_founded">
                <Input placeholder="如：2002年02月06日" />
              </Form.Item>
            </Col>
            <Col span={6}>
              <Form.Item label="经营期限" name="company_business_term">
                <Input placeholder="如：2002年02月06日至2032年02月05日" />
              </Form.Item>
            </Col>
          </Row>

          <Divider style={{ margin: '8px 0 16px' }} />
          <div style={sectionStyle}>法定代表人</div>
          <Row gutter={16}>
            <Col span={6}>
              <Form.Item label="姓名" name="legal_person_name">
                <Input />
              </Form.Item>
            </Col>
            <Col span={4}>
              <Form.Item label="性别" name="legal_person_gender">
                <Input placeholder="男 / 女" />
              </Form.Item>
            </Col>
            <Col span={4}>
              <Form.Item label="年龄" name="legal_person_age">
                <Input />
              </Form.Item>
            </Col>
            <Col span={10}>
              <Form.Item label="职务" name="legal_person_title">
                <Input placeholder="如：执行董事兼总经理" />
              </Form.Item>
            </Col>
          </Row>

          <Divider style={{ margin: '8px 0 16px' }} />
          <div style={sectionStyle}>授权代表（用于授权委托书）</div>
          <Row gutter={16}>
            <Col span={8}>
              <Form.Item label="授权代表姓名" name="authorized_rep_name">
                <Input placeholder="默认与法定代表人同人" />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item label="授权代表电话" name="authorized_rep_phone">
                <Input placeholder="授权代表手机号" />
              </Form.Item>
            </Col>
          </Row>
        </Form>
      </Spin>
    </Card>
  );
}
