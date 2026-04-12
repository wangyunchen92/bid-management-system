import { useEffect, useState, useCallback } from 'react';
import { useParams, useSearchParams, useNavigate } from 'react-router-dom';
import {
  Card, Form, Input, InputNumber, Select, DatePicker,
  Button, Space, Row, Col, Spin,  App } from 'antd';
import { SaveOutlined, ArrowLeftOutlined } from '@ant-design/icons';
import dayjs from 'dayjs';
import { getTender, createTender, updateTender } from '@/services/tender';
import { getUserList } from '@/services/system';
import useDictStore from '@/stores/useDictStore';

const { TextArea } = Input;

export default function TenderFormPage() {
  const { message } = App.useApp();
  const { id } = useParams<{ id: string }>();
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const { getDictItems } = useDictStore();
  const [form] = Form.useForm();

  const isEdit = !!id || searchParams.get('edit') === '1';
  const tenderId = id ? parseInt(id, 10) : undefined;

  const [loading, setLoading] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  const [tenderMethodOptions, setTenderMethodOptions] = useState<{ value: string; label: string }[]>([]);
  const [infoSourceOptions, setInfoSourceOptions] = useState<{ value: string; label: string }[]>([]);
  const [statusOptions, setStatusOptions] = useState<{ value: string; label: string }[]>([]);
  const [userOptions, setUserOptions] = useState<{ value: number; label: string }[]>([]);

  const loadDicts = useCallback(async () => {
    const [methods, sources, statuses] = await Promise.all([
      getDictItems('tender_method'),
      getDictItems('tender_info_source'),
      getDictItems('tender_status'),
    ]);
    setTenderMethodOptions(methods.map((d) => ({ value: d.item_value, label: d.item_label })));
    setInfoSourceOptions(sources.map((d) => ({ value: d.item_value, label: d.item_label })));
    setStatusOptions(statuses.map((d) => ({ value: d.item_value, label: d.item_label })));
  }, [getDictItems]);

  const loadUsers = useCallback(async () => {
    const res = await getUserList({ page: 1, page_size: 100 });
    setUserOptions(res.data.items.map((u: SystemUser) => ({ value: u.id, label: u.real_name })));
  }, []);

  const loadTender = useCallback(async () => {
    if (!tenderId) return;
    setLoading(true);
    try {
      const res = await getTender(tenderId);
      const t = res.data;
      form.setFieldsValue({
        ...t,
        deposit_deadline: t.deposit_deadline ? dayjs(t.deposit_deadline) : null,
        reg_deadline: t.reg_deadline ? dayjs(t.reg_deadline) : null,
        open_bid_time: t.open_bid_time ? dayjs(t.open_bid_time) : null,
      });
    } catch {
      message.error('加载招标信息失败');
    } finally {
      setLoading(false);
    }
  }, [tenderId, form]);

  useEffect(() => {
    loadDicts();
    loadUsers();
  }, [loadDicts, loadUsers]);

  useEffect(() => {
    if (tenderId) {
      loadTender();
    } else {
      form.setFieldsValue({ status: 'PENDING' });
    }
  }, [tenderId, loadTender, form]);

  const handleSubmit = async () => {
    try {
      const values = await form.validateFields();
      setSubmitting(true);

      // Convert dayjs to ISO string
      const payload: Partial<Tender> = { ...values };
      if (values.deposit_deadline) payload.deposit_deadline = values.deposit_deadline.toISOString();
      if (values.reg_deadline) payload.reg_deadline = values.reg_deadline.toISOString();
      if (values.open_bid_time) payload.open_bid_time = values.open_bid_time.toISOString();

      if (tenderId) {
        await updateTender(tenderId, payload);
        message.success('更新成功');
      } else {
        await createTender(payload);
        message.success('创建成功');
      }
      navigate('/tender/list');
    } catch (err: unknown) {
      if (err && typeof err === 'object' && 'errorFields' in err) {
        // validation error, antd handles it
        return;
      }
      message.error('保存失败');
    } finally {
      setSubmitting(false);
    }
  };

  const pageTitle = isEdit ? '编辑招标信息' : '新增招标信息';

  return (
    <div>
      <div style={{ marginBottom: 16, display: 'flex', alignItems: 'center', gap: 12 }}>
        <Button icon={<ArrowLeftOutlined />} onClick={() => navigate('/tender/list')}>
          返回列表
        </Button>
        <span style={{ fontSize: 18, fontWeight: 600, color: '#0f172a' }}>{pageTitle}</span>
      </div>

      <Spin spinning={loading}>
        <Form form={form} layout="vertical" requiredMark>
          {/* 基本信息 */}
          <Card title="基本信息" style={{ marginBottom: 16 }}>
            <Row gutter={24}>
              <Col span={12}>
                <Form.Item
                  name="title"
                  label="项目名称"
                  rules={[{ required: true, message: '请输入项目名称' }]}
                >
                  <Input placeholder="请输入项目名称" maxLength={200} />
                </Form.Item>
              </Col>
              <Col span={12}>
                <Form.Item name="tender_no" label="招标编号">
                  <Input placeholder="请输入招标编号" maxLength={100} />
                </Form.Item>
              </Col>
              <Col span={12}>
                <Form.Item name="tender_unit" label="招标单位">
                  <Input placeholder="请输入招标单位" maxLength={200} />
                </Form.Item>
              </Col>
              <Col span={6}>
                <Form.Item name="tender_method" label="招标方式">
                  <Select
                    placeholder="请选择招标方式"
                    allowClear
                    options={tenderMethodOptions}
                  />
                </Form.Item>
              </Col>
              <Col span={6}>
                <Form.Item name="info_source" label="信息来源">
                  <Select
                    placeholder="请选择信息来源"
                    allowClear
                    options={infoSourceOptions}
                  />
                </Form.Item>
              </Col>
            </Row>
          </Card>

          {/* 地区信息 */}
          <Card title="地区信息" style={{ marginBottom: 16 }}>
            <Row gutter={24}>
              <Col span={8}>
                <Form.Item name="province" label="省份">
                  <Input placeholder="请输入省份" maxLength={50} />
                </Form.Item>
              </Col>
              <Col span={8}>
                <Form.Item name="city" label="城市">
                  <Input placeholder="请输入城市" maxLength={50} />
                </Form.Item>
              </Col>
            </Row>
          </Card>

          {/* 财务信息 */}
          <Card title="财务信息" style={{ marginBottom: 16 }}>
            <Row gutter={24}>
              <Col span={8}>
                <Form.Item name="budget_amount" label="预算金额（万元）">
                  <InputNumber
                    placeholder="请输入预算金额"
                    precision={4}
                    min={0}
                    style={{ width: '100%' }}
                    addonAfter="万元"
                  />
                </Form.Item>
              </Col>
              <Col span={8}>
                <Form.Item name="deposit_amount" label="保证金金额（万元）">
                  <InputNumber
                    placeholder="请输入保证金金额"
                    precision={4}
                    min={0}
                    style={{ width: '100%' }}
                    addonAfter="万元"
                  />
                </Form.Item>
              </Col>
              <Col span={8}>
                <Form.Item name="deposit_deadline" label="保证金截止时间">
                  <DatePicker
                    showTime
                    placeholder="请选择截止时间"
                    style={{ width: '100%' }}
                    format="YYYY-MM-DD HH:mm"
                  />
                </Form.Item>
              </Col>
            </Row>
          </Card>

          {/* 时间信息 */}
          <Card title="时间信息" style={{ marginBottom: 16 }}>
            <Row gutter={24}>
              <Col span={8}>
                <Form.Item name="reg_deadline" label="报名截止时间">
                  <DatePicker
                    showTime
                    placeholder="请选择报名截止时间"
                    style={{ width: '100%' }}
                    format="YYYY-MM-DD HH:mm"
                  />
                </Form.Item>
              </Col>
              <Col span={8}>
                <Form.Item name="open_bid_time" label="开标时间">
                  <DatePicker
                    showTime
                    placeholder="请选择开标时间"
                    style={{ width: '100%' }}
                    format="YYYY-MM-DD HH:mm"
                  />
                </Form.Item>
              </Col>
            </Row>
          </Card>

          {/* 其他信息 */}
          <Card title="其他信息" style={{ marginBottom: 16 }}>
            <Row gutter={24}>
              <Col span={8}>
                <Form.Item name="status" label="跟进状态">
                  <Select
                    placeholder="请选择状态"
                    allowClear
                    options={
                      statusOptions.length > 0
                        ? statusOptions
                        : [
                            { value: 'PENDING', label: '待决策' },
                            { value: 'DECIDED_BID', label: '决定投标' },
                            { value: 'DECIDED_GIVE_UP', label: '决定放弃' },
                            { value: 'COMPOSING', label: '标书编制' },
                            { value: 'SUBMITTED', label: '已提交' },
                            { value: 'OPENED', label: '已开标' },
                          ]
                    }
                  />
                </Form.Item>
              </Col>
              <Col span={8}>
                <Form.Item name="follower_id" label="跟进人">
                  <Select
                    placeholder="请选择跟进人"
                    allowClear
                    options={userOptions}
                    showSearch
                    optionFilterProp="label"
                  />
                </Form.Item>
              </Col>
              <Col span={24}>
                <Form.Item name="remark" label="备注">
                  <TextArea rows={4} placeholder="请输入备注信息" maxLength={2000} showCount />
                </Form.Item>
              </Col>
            </Row>
          </Card>

          {/* 操作按钮 */}
          <div style={{ display: 'flex', justifyContent: 'center' }}>
            <Space>
              <Button onClick={() => navigate('/tender/list')}>取消</Button>
              <Button
                type="primary"
                icon={<SaveOutlined />}
                loading={submitting}
                onClick={handleSubmit}
                style={{ background: 'linear-gradient(135deg, #0d9488, #14b8a6)', border: 'none' }}
              >
                保存
              </Button>
            </Space>
          </div>
        </Form>
      </Spin>
    </div>
  );
}
